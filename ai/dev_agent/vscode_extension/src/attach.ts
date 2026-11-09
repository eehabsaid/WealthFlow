import * as fs from "node:fs";
import * as path from "node:path";

export const MAX_TEXT = 2_000_000;
export const MAX_IMAGE = 3_000_000;
const IMAGES: Record<string, string> = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp" };

export type Kind = "file" | "image";
export interface Chip {
  id: string;
  name: string;
  kind: Kind;
  size: number;
  chars?: number;
}
// What is sent to the server (the engine does the budgeting and the excerpt marking); kept in the extension host, never in the webview.
export interface Item {
  kind: Kind;
  name: string;
  text?: string;
  mime?: string;
  data?: string;
  path?: string;
}
export type Read = { ok: true; chip: Chip; item: Item } | { ok: false; name: string; reason: string };

// Read one file the user picked. Refuses what the engine could not use (binary files, wrong image types, huge files) with a plain reason; nothing is skipped silently.
export function readAttachment(file: string, kind: Kind, id: string, root?: string): Read {
  const name = path.basename(file);
  try {
    const size = fs.statSync(file).size;
    if (kind === "image") {
      const mime = IMAGES[path.extname(file).toLowerCase()];
      if (!mime) return { ok: false, name, reason: "only PNG, JPEG, GIF or WebP images" };
      if (size > MAX_IMAGE) return { ok: false, name, reason: "larger than 3 MB" };
      return { ok: true, chip: { id, name, kind, size }, item: { kind, name, mime, data: fs.readFileSync(file).toString("base64") } };
    }
    if (size > MAX_TEXT) return { ok: false, name, reason: "larger than 2 MB" };
    const buffer = fs.readFileSync(file);
    if (buffer.subarray(0, 8000).includes(0)) return { ok: false, name, reason: "this looks like a binary file" };
    const text = buffer.toString("utf8");
    const rel = root ? path.relative(root, file) : "";
    const inside = rel !== "" && !rel.startsWith("..") && !path.isAbsolute(rel);
    return { ok: true, chip: { id, name, kind, size, chars: text.length }, item: { kind, name, text, ...(inside ? { path: rel.split(path.sep).join("/") } : {}) } };
  } catch (error) {
    return { ok: false, name, reason: (error as Error).message };
  }
}
