import express from 'express';
import cors from 'cors';
import multer from 'multer';
import path from 'path';
import { fileURLToPath } from 'url';
import { db } from './db.js';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = parseInt(process.env.PORT || '3456', 10);
app.use(cors());
app.use(express.json());
app.use('/uploads', express.static(path.join(__dirname, '../uploads')));
const storage = multer.diskStorage({
    destination: (_req, _file, cb) => {
        cb(null, path.join(__dirname, '../uploads'));
    },
    filename: (_req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9);
        cb(null, uniqueSuffix + path.extname(file.originalname));
    },
});
const upload = multer({ storage });
// ─── versions ──────────────────────────────────────────────────
app.get('/api/versions', (_req, res) => {
    const rows = db.prepare('SELECT * FROM versions ORDER BY created_at ASC').all();
    res.json(rows);
});
app.post('/api/versions', (req, res) => {
    const { name } = req.body;
    if (!name || !name.trim()) {
        res.status(400).json({ error: '版本名不能为空' });
        return;
    }
    try {
        const result = db.prepare('INSERT INTO versions (name) VALUES (?)').run(name.trim());
        res.json({ id: result.lastInsertRowid, name: name.trim() });
    }
    catch (e) {
        if (e.message?.includes('UNIQUE')) {
            res.status(400).json({ error: '该版本名已存在' });
        }
        else {
            throw e;
        }
    }
});
// ─── shield items ───────────────────────────────────────────────
app.get('/api/shield-items', (req, res) => {
    const version = req.query.version;
    const rows = version
        ? db.prepare('SELECT * FROM shield_items WHERE version = ? ORDER BY id').all(version)
        : db.prepare('SELECT * FROM shield_items ORDER BY id').all();
    res.json(rows);
});
app.post('/api/shield-items/import', (req, res) => {
    const { items, version } = req.body;
    if (!Array.isArray(items) || items.length === 0) {
        res.status(400).json({ error: '请提供有效的项目数组' });
        return;
    }
    const insert = db.prepare('INSERT INTO shield_items (name, category, subsystem, version) VALUES (?, ?, ?, ?)');
    const insertMany = db.transaction((rows) => {
        for (const item of rows) {
            insert.run(item.name, item.category ?? null, item.subsystem ?? null, version ?? item.version ?? null);
        }
    });
    insertMany(items);
    res.json({ imported: items.length });
});
app.put('/api/shield-items/:id', (req, res) => {
    const { id } = req.params;
    const { name, category, subsystem, version } = req.body;
    if (!name) {
        res.status(400).json({ error: '名称不能为空' });
        return;
    }
    const stmt = db.prepare('UPDATE shield_items SET name = ?, category = ?, subsystem = ?, version = ? WHERE id = ?');
    const result = stmt.run(name, category ?? null, subsystem ?? null, version ?? null, id);
    if (result.changes === 0) {
        res.status(404).json({ error: '未找到该记录' });
        return;
    }
    res.json({ success: true });
});
app.delete('/api/shield-items/:id', (req, res) => {
    const { id } = req.params;
    // 检查是否有引用
    const ref = db.prepare('SELECT COUNT(*) as count FROM application_items WHERE shield_item_id = ?').get(id);
    if (ref.count > 0) {
        res.status(400).json({ error: '该屏蔽项已被引用，无法删除' });
        return;
    }
    const stmt = db.prepare('DELETE FROM shield_items WHERE id = ?');
    const result = stmt.run(id);
    if (result.changes === 0) {
        res.status(404).json({ error: '未找到该记录' });
        return;
    }
    res.json({ success: true });
});
// ─── applications ───────────────────────────────────────────────
app.post('/api/applications', upload.fields([
    { name: 'meetingMinutes', maxCount: 1 },
    { name: 'shieldScreenshot', maxCount: 1 },
]), (req, res) => {
    const { applicant, reason, expectedRestoreTime, shieldItemIds, version } = req.body;
    const files = req.files;
    if (!applicant || !reason || !expectedRestoreTime || !shieldItemIds) {
        res.status(400).json({ error: '缺少必填字段' });
        return;
    }
    let itemIds;
    try {
        itemIds = JSON.parse(shieldItemIds);
        if (!Array.isArray(itemIds) || itemIds.length === 0)
            throw new Error();
    }
    catch {
        res.status(400).json({ error: 'shieldItemIds 必须是有效的数字数组' });
        return;
    }
    const meetingMinutesPath = files?.meetingMinutes?.[0]?.filename ?? null;
    const shieldScreenshotPath = files?.shieldScreenshot?.[0]?.filename ?? null;
    const insertApp = db.prepare(`INSERT INTO applications (applicant, reason, meeting_minutes_path, shield_screenshot_path, expected_restore_time, version)
       VALUES (?, ?, ?, ?, ?, ?)`);
    const insertItem = db.prepare('INSERT INTO application_items (application_id, shield_item_id) VALUES (?, ?)');
    const result = db.transaction(() => {
        const appResult = insertApp.run(applicant, reason, meetingMinutesPath, shieldScreenshotPath, expectedRestoreTime, version ?? null);
        const applicationId = appResult.lastInsertRowid;
        for (const itemId of itemIds) {
            insertItem.run(applicationId, itemId);
        }
        return applicationId;
    })();
    res.json({ id: result });
});
app.get('/api/applications', (req, res) => {
    const version = req.query.version;
    const search = req.query.search;
    const sortField = req.query.sortField || 'created_at';
    const sortOrder = req.query.sortOrder === 'ascend' ? 'ASC' : 'DESC';
    // 白名单排序字段防止 SQL 注入
    const allowedSort = ['id', 'applicant', 'reason', 'expected_restore_time', 'status', 'total_items', 'active_items', 'created_at'];
    const safeField = allowedSort.includes(sortField) ? sortField : 'created_at';
    const conditions = [];
    const params = [];
    if (version) {
        conditions.push('a.version = ?');
        params.push(version);
    }
    if (search) {
        const like = `%${search}%`;
        conditions.push(`(a.applicant LIKE ? OR a.reason LIKE ? OR EXISTS (
      SELECT 1 FROM application_items ai2
      JOIN shield_items si ON ai2.shield_item_id = si.id
      WHERE ai2.application_id = a.id AND si.name LIKE ?
    ))`);
        params.push(like, like, like);
    }
    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const rows = db
        .prepare(`SELECT a.*,
        (SELECT COUNT(*) FROM application_items WHERE application_id = a.id) as total_items,
        (SELECT COUNT(*) FROM application_items WHERE application_id = a.id AND status = 'active') as active_items
       FROM applications a
       ${where}
       ORDER BY a.${safeField} ${sortOrder}`)
        .all(...params);
    res.json(rows);
});
// 获取某作业下的屏蔽项清单
app.get('/api/applications/:id/items', (req, res) => {
    const { id } = req.params;
    const rows = db
        .prepare(`SELECT
        ai.id,
        ai.shield_item_id,
        ai.status,
        si.name as shield_item_name,
        si.category as shield_item_category,
        si.subsystem as shield_item_subsystem
      FROM application_items ai
      JOIN shield_items si ON ai.shield_item_id = si.id
      WHERE ai.application_id = ?
      ORDER BY si.id`)
        .all(id);
    res.json(rows);
});
// 完成作业（支持 dryRun 预检查）
app.post('/api/applications/:id/complete', (req, res) => {
    const { id } = req.params;
    const { restoredBy, itemIds, dryRun, force } = req.body;
    // 查询该作业下所有 active 的屏蔽项
    const activeItems = db
        .prepare(`SELECT ai.id, ai.shield_item_id, si.name as shield_item_name
       FROM application_items ai
       JOIN shield_items si ON ai.shield_item_id = si.id
       WHERE ai.application_id = ? AND ai.status = 'active'`)
        .all(id);
    if (activeItems.length === 0) {
        res.json({ canComplete: true, conflicts: [], items: [] });
        return;
    }
    // 获取该申请版本，冲突检测只限同版本
    const appVersion = db.prepare('SELECT version FROM applications WHERE id = ?').get(id)?.version;
    // 检查每个屏蔽项是否有冲突（其他 active 作业，同版本）
    const getConflicts = db.prepare(`SELECT a.id, a.applicant, a.reason
     FROM application_items ai
     JOIN applications a ON ai.application_id = a.id
     WHERE ai.shield_item_id = ? AND ai.application_id != ? AND ai.status = 'active'
     ${appVersion ? 'AND a.version = ?' : ''}`);
    const conflicts = [];
    for (const item of activeItems) {
        const conflictRows = getConflicts.all(...(appVersion ? [item.shield_item_id, id, appVersion] : [item.shield_item_id, id]));
        for (const c of conflictRows) {
            conflicts.push({
                itemId: item.id,
                shieldItemId: item.shield_item_id,
                shieldItemName: item.shield_item_name,
                conflictApplicationId: c.id,
                applicant: c.applicant,
                reason: c.reason,
            });
        }
    }
    if (conflicts.length > 0 && !force) {
        res.json({
            canComplete: false,
            conflicts,
            items: activeItems,
            message: '存在冲突，请勿在设备上解除',
        });
        return;
    }
    // dryRun 模式：只返回信息，不执行
    if (dryRun) {
        res.json({ canComplete: true, conflicts: [], items: activeItems });
        return;
    }
    // 真正执行恢复
    const targetIds = Array.isArray(itemIds) && itemIds.length > 0
        ? itemIds
        : activeItems.map((i) => i.id);
    const updateApp = db.prepare(`UPDATE applications SET status = 'restored', restored_at = datetime('now', 'localtime'), restored_by = ? WHERE id = ?`);
    const updateItems = db.prepare(`UPDATE application_items SET status = 'restored', restored_at = datetime('now', 'localtime'), restored_by = ?
     WHERE id = ? AND status = 'active'`);
    db.transaction(() => {
        updateApp.run(restoredBy || '系统', id);
        for (const itemId of targetIds) {
            updateItems.run(restoredBy || '系统', itemId);
        }
    })();
    res.json({ success: true, restored: targetIds.length });
});
// ─── ledger ─────────────────────────────────────────────────────
app.get('/api/ledger', (req, res) => {
    const now = new Date().toISOString();
    const version = req.query.version;
    const rows = db
        .prepare(`SELECT
        ai.id,
        ai.application_id,
        ai.shield_item_id,
        ai.status,
        ai.restored_at,
        ai.restored_by,
        ai.created_at,
        si.name as shield_item_name,
        si.category as shield_item_category,
        si.subsystem as shield_item_subsystem,
        si.version as shield_item_version,
        a.applicant,
        a.reason,
        a.meeting_minutes_path,
        a.shield_screenshot_path,
        a.expected_restore_time,
        a.status as application_status,
        a.created_at as application_created_at
      FROM application_items ai
      JOIN shield_items si ON ai.shield_item_id = si.id
      JOIN applications a ON ai.application_id = a.id
      WHERE ai.status = 'active'
      ${version ? 'AND a.version = ?' : ''}
      ORDER BY
        CASE WHEN a.expected_restore_time < ? THEN 0 ELSE 1 END,
        a.expected_restore_time ASC`)
        .all(...(version ? [version, now] : [now]));
    res.json(rows);
});
// ─── history ────────────────────────────────────────────────────
app.get('/api/history', (req, res) => {
    const version = req.query.version;
    const rows = db
        .prepare(`SELECT
        ai.id,
        ai.application_id,
        ai.shield_item_id,
        ai.status,
        ai.restored_at,
        ai.restored_by,
        ai.created_at,
        si.name as shield_item_name,
        si.category as shield_item_category,
        si.subsystem as shield_item_subsystem,
        si.version as shield_item_version,
        a.applicant,
        a.reason,
        a.meeting_minutes_path,
        a.shield_screenshot_path,
        a.expected_restore_time,
        a.created_at as application_created_at,
        (SELECT COUNT(*) FROM application_items WHERE shield_item_id = ai.shield_item_id) as shield_count
      FROM application_items ai
      JOIN shield_items si ON ai.shield_item_id = si.id
      JOIN applications a ON ai.application_id = a.id
      WHERE ai.status = 'restored'
      ${version ? 'AND a.version = ?' : ''}
      ORDER BY ai.restored_at DESC`)
        .all(...(version ? [version] : []));
    res.json(rows);
});
// ─── delete application ──────────────────────────────────────────
// ─── stats ─────────────────────────────────────────────────────
app.get('/api/stats', (req, res) => {
    const version = req.query.version;
    const now = new Date().toISOString();

    const params = [];
    let versionClause = '';
    if (version) {
        versionClause = 'AND a.version = ?';
        params.push(version);
    }

    const row = db
        .prepare(`SELECT
        COUNT(*) as total_apps,
        COALESCE(SUM(
          (SELECT COUNT(*) FROM application_items WHERE application_id = a.id AND status = 'active')
        ), 0) as total_active,
        COALESCE(SUM(
          CASE WHEN a.expected_restore_time < ? THEN
            (SELECT COUNT(*) FROM application_items WHERE application_id = a.id AND status = 'active')
          ELSE 0 END
        ), 0) as total_overdue
      FROM applications a
      WHERE a.status = 'active' ${versionClause}`)
        .get(now, ...params);

    res.json({
        totalApps: row.total_apps,
        totalActive: row.total_active,
        totalOverdue: row.total_overdue,
    });
});

app.delete('/api/applications/:id', (req, res) => {
    const { id } = req.params;
    const app = db.prepare('SELECT id, status FROM applications WHERE id = ?').get(id);
    if (!app) {
        res.status(404).json({ error: '未找到该申请记录' });
        return;
    }
    const deleteItems = db.prepare('DELETE FROM application_items WHERE application_id = ?');
    const deleteApp = db.prepare('DELETE FROM applications WHERE id = ?');
    db.transaction(() => {
        deleteItems.run(id);
        deleteApp.run(id);
    })();
    res.json({ success: true });
});
app.listen(PORT, () => {
    console.log(`安全联锁屏蔽后端服务已启动: http://localhost:${PORT}`);
});
