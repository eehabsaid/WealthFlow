"""Style, script and labels of the user-guide HTML page (one self-contained file: no network, no external font or script).
Logical CSS properties make the same sheet work left-to-right and right-to-left (Arabic)."""

from __future__ import annotations

LABELS = {
    "en": {"contents": "Contents", "skip": "Skip to main content", "toggle": "Toggle table of contents"},
    "ar": {"contents": "المحتويات", "skip": "تخطي إلى المحتوى الرئيسي", "toggle": "إظهار أو إخفاء المحتويات"},
    "fr": {"contents": "Sommaire", "skip": "Aller au contenu principal", "toggle": "Afficher ou masquer le sommaire"},
    "de": {"contents": "Inhalt", "skip": "Zum Hauptinhalt springen", "toggle": "Inhaltsverzeichnis ein- oder ausblenden"},
}

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#f8f9fa;--card:#fff;--text:#212529;--muted:#6c757d;--accent:#0d6efd;--accent-light:#cfe2ff;--border:#dee2e6;--side:290px;--r:8px}
@media(prefers-color-scheme:dark){:root{--bg:#121212;--card:#1e1e1e;--text:#e0e0e0;--muted:#9e9e9e;--accent:#4dabf7;--accent-light:#1a3a5c;--border:#333}}
html{scroll-behavior:smooth;scroll-padding-top:1rem}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Tahoma,sans-serif;background:var(--bg);color:var(--text);line-height:1.65;font-size:15px}
.skip-link{position:absolute;top:-100%;inset-inline-start:0;background:var(--accent);color:#fff;padding:.5rem 1rem;z-index:9999;text-decoration:none;font-weight:600}
.skip-link:focus{top:0}
.layout{display:flex;min-height:100vh}
.toc-rail{position:sticky;top:0;width:var(--side);height:100vh;overflow-y:auto;background:var(--card);border-inline-end:1px solid var(--border);padding:1rem .75rem;flex-shrink:0}
.toc-rail h2{font-size:.85rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-bottom:.75rem}
.toc-rail ul{list-style:none}
.toc-rail a{display:block;padding:.3rem .5rem;border-radius:var(--r);color:var(--text);text-decoration:none;font-size:.85rem}
.toc-rail a:hover,.toc-rail a:focus{background:var(--accent-light);color:var(--accent);outline:none}
.toc-rail a.active{background:var(--accent);color:#fff;font-weight:600}
.toc-sub{display:none;padding-inline-start:.9rem}
.toc-l1.current>.toc-sub{display:block}
.toc-sub a{font-size:.8rem;color:var(--muted)}
main{flex:1;padding:2rem 2.5rem;max-width:880px;min-width:0}
main>header{margin-bottom:1.5rem}
main>header h1{font-size:2rem;line-height:1.25;margin-bottom:.4rem}
.meta{color:var(--muted)}
.guide-section{margin-bottom:2.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border)}
.guide-section:last-child{border-bottom:none}
.section-heading{font-size:1.45rem;line-height:1.3;margin-bottom:.75rem}
.sub-heading{font-size:1.1rem;margin:1.2rem 0 .4rem}
.sub-heading.l4{font-size:1rem;color:var(--muted)}
.purpose{margin-bottom:.75rem}
.steps{padding-inline-start:1.5rem;margin:.5rem 0}
.notes{padding-inline-start:1.5rem;margin:.5rem 0;list-style:disc}
.steps li,.notes li{margin:.3rem 0}
.notes li{color:var(--muted)}
.table-wrap{overflow-x:auto;margin:.75rem 0}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{border:1px solid var(--border);padding:.4rem .6rem;text-align:start}
th{background:var(--accent-light)}
.toc-toggle{display:none;position:fixed;top:.75rem;inset-inline-start:.75rem;z-index:1000;background:var(--accent);color:#fff;border:none;border-radius:var(--r);padding:.5rem .75rem;font-size:1rem;cursor:pointer}
@media(max-width:768px){.toc-toggle{display:block}
.toc-rail{position:fixed;inset-inline-start:0;top:0;transform:translateX(-100%);transition:transform .25s ease;z-index:999;width:270px}
[dir=rtl] .toc-rail{transform:translateX(100%)}
.toc-rail.open,[dir=rtl] .toc-rail.open{transform:translateX(0)}
main{padding:4rem 1rem 2rem}}
@media print{.toc-rail,.toc-toggle,.skip-link{display:none!important}main{max-width:100%;padding:0}.guide-section{break-inside:avoid-page}body{background:#fff;color:#000;font-size:12pt}}
"""

JS = """
(function(){var b=document.getElementById("tocToggle"),r=document.getElementById("tocRail");
b.addEventListener("click",function(){var o=r.classList.toggle("open");b.setAttribute("aria-expanded",o?"true":"false")});
r.querySelectorAll("a").forEach(function(a){a.addEventListener("click",function(){if(window.innerWidth<=768){r.classList.remove("open");b.setAttribute("aria-expanded","false")}})});})();
(function(){var links=document.querySelectorAll(".toc-rail a[data-target]"),map={};
links.forEach(function(a){map[a.getAttribute("data-target")]=a});
var secs=document.querySelectorAll(".guide-section");if(!("IntersectionObserver" in window))return;
var vis=new Map();
function show(sec){links.forEach(function(a){a.classList.remove("active")});
document.querySelectorAll(".toc-l1.current").forEach(function(l){l.classList.remove("current")});
var a=map[sec.id];if(!a)return;a.classList.add("active");a.parentNode.classList.add("current");a.scrollIntoView({block:"nearest"})}
var obs=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)vis.set(e.target.id,e.target);else vis.delete(e.target.id)});
var top=null;vis.forEach(function(s){if(!top||s.getBoundingClientRect().top<top.getBoundingClientRect().top)top=s});
if(top)show(top)},{rootMargin:"0px 0px -60% 0px",threshold:0});
secs.forEach(function(s){obs.observe(s)});})();
"""
