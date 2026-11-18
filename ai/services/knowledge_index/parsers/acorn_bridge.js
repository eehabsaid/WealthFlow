#!/usr/bin/env node
// Structural JS indexer on top of Acorn. stdin: {"acorn": "<path to acorn>", "files": [{"path": rel, "abs": abs}]}
// stdout: {rel: {symbols: [...], refs: [...]}} or {rel: {error: "..."}}. Script-global aware: top-level declarations and
// window.X assignments are globals; identifier references shadowed by a local declaration are NOT reported.
"use strict";
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const acorn = require(input.acorn);
const FUNC = new Set(["FunctionDeclaration", "FunctionExpression", "ArrowFunctionExpression"]);
const isFn = (n) => n && (FUNC.has(n.type) || n.type === "ClassExpression");

function parse(code) {
  const opts = {ecmaVersion: "latest", locations: true, allowHashBang: true, allowReturnOutsideFunction: true};
  try { return acorn.parse(code, {...opts, sourceType: "script"}); }
  catch (e) { return acorn.parse(code, {...opts, sourceType: "module"}); }
}

function patternNames(p, out) {
  if (!p) return;
  if (p.type === "Identifier") out.add(p.name);
  else if (p.type === "ObjectPattern") p.properties.forEach((x) => patternNames(x.value || x.argument, out));
  else if (p.type === "ArrayPattern") p.elements.forEach((x) => patternNames(x, out));
  else if (p.type === "RestElement") patternNames(p.argument, out);
  else if (p.type === "AssignmentPattern") patternNames(p.left, out);
}

function declaredIn(body, out) {   // names declared directly in a scope (not inside nested functions)
  const visit = (n) => {
    if (!n || typeof n.type !== "string") return;
    if (n.type === "VariableDeclaration") n.declarations.forEach((d) => patternNames(d.id, out));
    if (n.type === "FunctionDeclaration" || n.type === "ClassDeclaration") { if (n.id) out.add(n.id.name); return; }
    if (n.type === "CatchClause" && n.param) patternNames(n.param, out);
    if (FUNC.has(n.type)) return;
    for (const k of Object.keys(n)) {
      const v = n[k];
      if (Array.isArray(v)) v.forEach(visit); else if (v && typeof v.type === "string") visit(v);
    }
  };
  (Array.isArray(body) ? body : [body]).forEach(visit);
}

function indexFile(code) {
  const ast = parse(code), symbols = [], refs = [];
  const sym = (name, kind, node, parent, scope) => symbols.push({name, kind, line: node.loc.start.line, end: node.loc.end.line, parent: parent || "", scope});
  const walk = (n, scopes, src) => {
    if (!n || typeof n.type !== "string") return;
    const top = scopes.length === 1;
    if (n.type === "FunctionDeclaration" && n.id && top) { sym(n.id.name, "function", n, "", "global"); src = n.id.name; }
    else if (n.type === "ClassDeclaration" && n.id && top) { sym(n.id.name, "class", n, "", "global"); src = n.id.name; }
    else if (n.type === "MethodDefinition" && n.key && n.key.name) { sym(n.key.name, "method", n, src, "member"); src = (src ? src + "." : "") + n.key.name; }
    else if (n.type === "VariableDeclaration" && top) {
      n.declarations.forEach((d) => { if (d.id.type === "Identifier") sym(d.id.name, isFn(d.init) ? "function" : "variable", d, "", "global"); });
    } else if (n.type === "AssignmentExpression" && n.left.type === "MemberExpression" && !n.left.computed && n.left.property.type === "Identifier") {
      const o = n.left.object, name = n.left.property.name;
      if (o.type === "Identifier" && (o.name === "window" || o.name === "globalThis")) sym(name, isFn(n.right) ? "function" : "variable", n, "", "global");
      else if (o.type === "Identifier" && top) sym(name, isFn(n.right) ? "function" : "variable", n, o.name, "member:" + o.name);
    }
    let inner = scopes;
    if (FUNC.has(n.type)) {
      const names = new Set(); n.params.forEach((p) => patternNames(p, names));
      declaredIn(n.body.type === "BlockStatement" ? n.body.body : [n.body], names);
      if (n.type === "FunctionExpression" && n.id) names.add(n.id.name);
      inner = [...scopes, names];
    }
    if (n.type === "CallExpression") {
      const c = n.callee;
      if (c.type === "Identifier") refs.push({line: n.loc.start.line, src, name: c.name, kind: "call"});
      else if (c.type === "MemberExpression" && !c.computed && c.property.type === "Identifier") refs.push({line: n.loc.start.line, src, name: c.property.name, kind: "call"});
    }
    if (n.type === "Identifier" && !(n.__skip)) {
      if (!scopes.slice(1).some((s) => s.has(n.name))) refs.push({line: n.loc.start.line, src, name: n.name, kind: "ident"});
    }
    for (const k of Object.keys(n)) {
      if (k === "loc") continue;
      const v = n[k];
      const child = (c) => {
        if (!c || typeof c.type !== "string") return;
        if (c.type === "Identifier" && ((n.type === "MemberExpression" && k === "property" && !n.computed) ||
            (n.type === "Property" && k === "key" && !n.computed) || (n.type === "MethodDefinition" && k === "key") ||
            (n.type === "PropertyDefinition" && k === "key") || k === "label")) {
          if (n.type === "MemberExpression" && n.object.type === "Identifier" && (n.object.name === "window" || n.object.name === "globalThis"))
            refs.push({line: c.loc.start.line, src, name: c.name, kind: "ident"});
          return;
        }
        walk(c, inner, src);
      };
      if (Array.isArray(v)) v.forEach(child); else child(v);
    }
  };
  const globals = new Set();
  walk(ast, [globals], "");
  return {symbols, refs};
}

const out = {};
for (const f of input.files) {
  try { out[f.path] = indexFile(fs.readFileSync(f.abs, "utf8")); }
  catch (e) { out[f.path] = {error: String(e.message || e)}; }
}
process.stdout.write(JSON.stringify(out));
