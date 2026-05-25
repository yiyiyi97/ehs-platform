import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dbPath = path.join(__dirname, '../data.db');
export const db = new Database(dbPath);
db.pragma('journal_mode = WAL');
export function initDb() {
    db.exec(`
    CREATE TABLE IF NOT EXISTS shield_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      code TEXT,
      location TEXT,
      category TEXT,
      subsystem TEXT,
      version TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS applications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      applicant TEXT NOT NULL,
      reason TEXT NOT NULL,
      meeting_minutes_path TEXT,
      shield_screenshot_path TEXT,
      expected_restore_time TEXT NOT NULL,
      version TEXT,
      status TEXT NOT NULL DEFAULT 'active',
      created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
      restored_at TEXT,
      restored_by TEXT
    );

    CREATE TABLE IF NOT EXISTS application_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      application_id INTEGER NOT NULL,
      shield_item_id INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'active',
      restored_at TEXT,
      restored_by TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
      FOREIGN KEY (application_id) REFERENCES applications(id),
      FOREIGN KEY (shield_item_id) REFERENCES shield_items(id)
    );
  `);
    // 迁移：添加 subsystem 列（如果不存在）
    const columns = db.prepare("PRAGMA table_info(shield_items)").all();
    if (!columns.some((c) => c.name === 'subsystem')) {
        db.exec('ALTER TABLE shield_items ADD COLUMN subsystem TEXT');
    }
    if (!columns.some((c) => c.name === 'version')) {
        db.exec('ALTER TABLE shield_items ADD COLUMN version TEXT');
    }
    // applications migration
    const appCols = db.prepare("PRAGMA table_info(applications)").all();
    if (!appCols.some((c) => c.name === 'version')) {
        db.exec('ALTER TABLE applications ADD COLUMN version TEXT');
    }
    // ── versions table ──
    db.exec(`
    CREATE TABLE IF NOT EXISTS versions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
  `);
    // seed alpha1 if no versions exist
    const vc = db.prepare('SELECT COUNT(*) as count FROM versions').get();
    if (vc.count === 0) {
        db.prepare('INSERT INTO versions (name) VALUES (?)').run('alpha1');
    }
    // migrate existing NULL versions to 'alpha1'
    db.prepare("UPDATE shield_items SET version = 'alpha1' WHERE version IS NULL").run();
    db.prepare("UPDATE applications SET version = 'alpha1' WHERE version IS NULL").run();
}
initDb();
