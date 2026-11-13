from html.parser import HTMLParser

class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errs = []
    def handle_starttag(self, t, a):
        if t not in ('br', 'hr', 'img', 'meta', 'link', 'input', 'col'):
            self.stack.append(t)
    def handle_endtag(self, t):
        if self.stack and self.stack[-1] == t:
            self.stack.pop()
        else:
            self.errs.append('mismatch ' + t + ' at ' + str(self.getpos()))

p = P()
p.feed(open('docs/user-guide-ar.html', encoding='utf-8').read())
print('errors:', p.errs[:10])
print('unclosed:', p.stack[:10])
