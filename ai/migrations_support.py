"""Helpers for ai/migrations/0001_initial (kept out of the migration file)."""
from django.db import migrations
from django.db.migrations.loader import MigrationLoader

OLD_LABEL, NEW_LABEL = "core", "ai"
MODELS = ["aiknowledgeentry", "aipromptcategory", "aiconversation", "aimemorynote", "aimessage",
          "aichatblock", "aiattachment", "aiprompt", "aianswerfeedback"]
# The host app whose history already creates these tables (WealthFlow's core app).
CORE_CREATOR = ("core", "0040_ai_blocks_attachments")


def _core_history_creates_tables(connection):
    """True when another migration chain will create (or has created) the tables."""
    return CORE_CREATOR in MigrationLoader(connection, ignore_no_migrations=True).graph.nodes


class CreateModelIfMissing(migrations.CreateModel):
    """CreateModel whose database part is skipped if the table exists or core will create it."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        table = model._meta.db_table
        if table in schema_editor.connection.introspection.table_names():
            return
        if _core_history_creates_tables(schema_editor.connection):
            return
        schema_editor.create_model(model)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Never drop data when this migration is reversed."""


def _assigned(apps, db, ct_row):
    """True if any permission of this content type is given to a group or a user."""
    from django.contrib.auth.models import Permission as perm
    from django.db.models import Q
    return perm.objects.using(db).filter(content_type=ct_row).filter(
        Q(group__isnull=False) | Q(user__isnull=False)).exists()


def _relabel(apps, schema_editor, src, dst):
    """Move ContentType rows src -> dst keeping the OLDEST id; drop an unassigned duplicate."""
    if "django_content_type" not in schema_editor.connection.introspection.table_names():
        return
    # Current models on purpose: this migration does not depend on contenttypes/auth state versions.
    from django.contrib.contenttypes.models import ContentType as ct
    db = schema_editor.connection.alias
    for name in MODELS:
        rows = list(ct.objects.using(db).filter(app_label__in=[src, dst], model=name).order_by("id"))
        if not rows or (len(rows) == 1 and rows[0].app_label == dst):
            continue
        keep, extra = rows[0], rows[1:]
        if any(_assigned(apps, db, r) for r in extra):
            continue
        for r in extra:
            r.delete()
        if keep.app_label != dst:
            keep.app_label = dst
            keep.save(using=db)


def relabel_forward(apps, schema_editor):
    _relabel(apps, schema_editor, OLD_LABEL, NEW_LABEL)


def relabel_backward(apps, schema_editor):
    _relabel(apps, schema_editor, NEW_LABEL, OLD_LABEL)
