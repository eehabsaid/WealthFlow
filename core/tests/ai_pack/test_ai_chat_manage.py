"""Sidebar order (a new message moves its chat to the top) and chat management: rename, search across chats, edit-and-resend."""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from ai.models.ai_conversation import AIConversation
from ai.models.ai_message import AIMessage
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
API = "/api/financial-advisor/ai/"


class ChatManageBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")
        self.other = User.objects.create_user(username="other", password="pw12345!")
        for u in (self.user, self.other):
            grant_ai_workspace_access(u)
        self.client.force_login(self.user)

    def chat(self, title, user=None):
        return AIConversation.objects.create(user=user or self.user, title=title)

    def ids(self):
        return [c["id"] for c in self.client.get(API + "conversations/").json()["conversations"]]


class SidebarOrderTests(ChatManageBase):
    def test_new_message_moves_an_old_chat_to_the_top(self):
        old, new = self.chat("old chat"), self.chat("new chat")
        AIConversation.objects.filter(pk=old.pk).update(updated_at=timezone.now() - datetime.timedelta(days=10))
        self.assertEqual(self.ids(), [new.id, old.id])
        AIMessage.objects.create(conversation=old, role="user", content="hello again")
        self.assertEqual(self.ids(), [old.id, new.id])

    def test_assistant_reply_also_moves_the_chat_and_system_rows_do_not(self):
        a, b = self.chat("a"), self.chat("b")
        AIConversation.objects.filter(pk=a.pk).update(updated_at=timezone.now() - datetime.timedelta(days=2))
        AIMessage.objects.create(conversation=a, role="system", content="internal")
        self.assertEqual(self.ids(), [b.id, a.id])
        AIMessage.objects.create(conversation=a, role="assistant", content="answer")
        self.assertEqual(self.ids(), [a.id, b.id])

    def test_editing_a_message_does_not_move_the_chat(self):
        a, b = self.chat("a"), self.chat("b")
        msg = AIMessage.objects.create(conversation=a, role="user", content="x")
        AIConversation.objects.filter(pk=a.pk).update(updated_at=timezone.now() - datetime.timedelta(days=3))
        msg.content = "y"
        msg.save()
        self.assertEqual(self.ids(), [b.id, a.id])


class RenameTests(ChatManageBase):
    def test_rename_trims_and_keeps_position(self):
        a, b = self.chat("a"), self.chat("b")
        res = self.client.patch(API + f"conversations/{a.id}/", data={"title": "  My   budget  "}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(AIConversation.objects.get(pk=a.pk).title, "My budget")
        self.assertEqual(self.ids(), [b.id, a.id])

    def test_empty_title_rejected_and_long_title_capped(self):
        a = self.chat("a")
        self.assertEqual(self.client.patch(API + f"conversations/{a.id}/", data={"title": "   "}, content_type="application/json").status_code, 400)
        self.client.patch(API + f"conversations/{a.id}/", data={"title": "x" * 500}, content_type="application/json")
        self.assertEqual(len(AIConversation.objects.get(pk=a.pk).title), 80)

    def test_cannot_rename_someone_elses_chat(self):
        theirs = self.chat("theirs", self.other)
        res = self.client.patch(API + f"conversations/{theirs.id}/", data={"title": "mine now"}, content_type="application/json")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(AIConversation.objects.get(pk=theirs.pk).title, "theirs")


class SearchTests(ChatManageBase):
    def search(self, q):
        return self.client.get(API + "conversations/search/", {"q": q}).json()["results"]

    def test_finds_by_title_and_by_message_text(self):
        t = self.chat("Gold purchase plan")
        m = self.chat("Chat two")
        AIMessage.objects.create(conversation=m, role="user", content="How much is my gold worth today?")
        self.assertEqual({r["id"] for r in self.search("gold")}, {t.id, m.id})
        hit = [r for r in self.search("worth") if r["id"] == m.id][0]
        self.assertIn("worth", hit["snippet"])

    def test_one_result_per_chat_even_with_many_matching_messages(self):
        c = self.chat("c")
        for i in range(5):
            AIMessage.objects.create(conversation=c, role="user", content=f"rent question {i}")
        self.assertEqual(len(self.search("rent")), 1)

    def test_never_returns_other_users_or_deleted_content(self):
        theirs = self.chat("secret salary", self.other)
        AIMessage.objects.create(conversation=theirs, role="user", content="secret salary details")
        mine = self.chat("mine")
        gone = AIMessage.objects.create(conversation=mine, role="user", content="secret removed text")
        AIMessage.objects.filter(pk=gone.pk).update(is_deleted=True)
        dead = self.chat("secret deleted chat")
        AIConversation.objects.filter(pk=dead.pk).update(is_deleted=True)
        self.assertEqual(self.search("secret"), [])

    def test_short_query_returns_nothing(self):
        self.chat("abc")
        self.assertEqual(self.search("a"), [])


class RewindTests(ChatManageBase):
    def build(self):
        c = self.chat("c")
        m1 = AIMessage.objects.create(conversation=c, role="user", content="first")
        AIMessage.objects.create(conversation=c, role="assistant", content="reply 1")
        m2 = AIMessage.objects.create(conversation=c, role="user", content="second")
        AIMessage.objects.create(conversation=c, role="assistant", content="reply 2")
        return c, m1, m2

    def test_hides_the_edited_message_and_everything_after_it(self):
        c, m1, m2 = self.build()
        res = self.client.post(API + f"messages/{m2.id}/rewind/")
        self.assertEqual((res.status_code, res.json()["hidden"]), (200, 2))
        left = list(c.messages.filter(is_deleted=False).values_list("content", flat=True))
        self.assertEqual(left, ["first", "reply 1"])

    def test_first_message_rewinds_the_whole_chat(self):
        c, m1, _ = self.build()
        self.client.post(API + f"messages/{m1.id}/rewind/")
        self.assertEqual(c.messages.filter(is_deleted=False).count(), 0)

    def test_only_own_user_messages_can_be_rewound(self):
        c, _, _ = self.build()
        assistant = c.messages.filter(role="assistant").first()
        self.assertEqual(self.client.post(API + f"messages/{assistant.id}/rewind/").status_code, 404)
        theirs = self.chat("theirs", self.other)
        tm = AIMessage.objects.create(conversation=theirs, role="user", content="private")
        self.assertEqual(self.client.post(API + f"messages/{tm.id}/rewind/").status_code, 404)
        self.assertFalse(AIMessage.objects.get(pk=tm.pk).is_deleted)
