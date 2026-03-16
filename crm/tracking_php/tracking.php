<?php
/**
 * Dedolytics Tracking Pixel & Click-Through Server
 * Hosted on Hostinger alongside the dashboards.
 * 
 * Endpoints:
 *   /tracking/pixel.php?id=<tracking_id>        — Serves 1x1 GIF, logs open
 *   /tracking/click.php?id=<tracking_id>&url=<encoded_url>  — Logs click, redirects
 *   /tracking/api.php?since=<ISO_TS>            — Returns JSON of opens for pipeline sync
 */

// SQLite database for tracking events
$db_path = __DIR__ . '/tracking_events.db';

function get_db($db_path) {
    $db = new SQLite3($db_path);
    $db->exec('CREATE TABLE IF NOT EXISTS open_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id TEXT NOT NULL,
        opened_at DATETIME NOT NULL,
        user_agent TEXT,
        ip_address TEXT
    )');
    $db->exec('CREATE INDEX IF NOT EXISTS idx_tracking_id ON open_events(tracking_id)');
    $db->exec('CREATE INDEX IF NOT EXISTS idx_opened_at ON open_events(opened_at)');
    return $db;
}

// Determine which action to take based on the script name
$script = basename($_SERVER['SCRIPT_NAME']);

if ($script === 'pixel.php') {
    // ─── Tracking Pixel ─────────────────────────────────────────────────
    $tracking_id = $_GET['id'] ?? '';
    if ($tracking_id) {
        try {
            $db = get_db($db_path);
            $stmt = $db->prepare('INSERT INTO open_events (tracking_id, opened_at, user_agent, ip_address) VALUES (:tid, :ts, :ua, :ip)');
            $stmt->bindValue(':tid', $tracking_id, SQLITE3_TEXT);
            $stmt->bindValue(':ts', gmdate('Y-m-d H:i:s'), SQLITE3_TEXT);
            $stmt->bindValue(':ua', $_SERVER['HTTP_USER_AGENT'] ?? '', SQLITE3_TEXT);
            $stmt->bindValue(':ip', $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? '', SQLITE3_TEXT);
            $stmt->execute();
            $db->close();
        } catch (Exception $e) {
            // Never fail — always serve the pixel
        }
    }
    
    // Serve 1x1 transparent GIF
    header('Content-Type: image/gif');
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    header('Pragma: no-cache');
    header('Expires: 0');
    echo base64_decode('R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==');
    exit;

} elseif ($script === 'click.php') {
    // ─── Click-Through Tracking ──────────────────────────────────────────
    $tracking_id = $_GET['id'] ?? '';
    $redirect_url = $_GET['url'] ?? 'https://www.dedolytics.org';
    
    if ($tracking_id) {
        try {
            $db = get_db($db_path);
            $stmt = $db->prepare('INSERT INTO open_events (tracking_id, opened_at, user_agent, ip_address) VALUES (:tid, :ts, :ua, :ip)');
            $stmt->bindValue(':tid', $tracking_id, SQLITE3_TEXT);
            $stmt->bindValue(':ts', gmdate('Y-m-d H:i:s'), SQLITE3_TEXT);
            $stmt->bindValue(':ua', $_SERVER['HTTP_USER_AGENT'] ?? '', SQLITE3_TEXT);
            $stmt->bindValue(':ip', $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? '', SQLITE3_TEXT);
            $stmt->execute();
            $db->close();
        } catch (Exception $e) {
            // Never block the redirect
        }
    }
    
    header('Location: ' . $redirect_url);
    exit;

} elseif ($script === 'api.php') {
    // ─── Sync API ────────────────────────────────────────────────────────
    $since = $_GET['since'] ?? '2000-01-01T00:00:00';
    
    header('Content-Type: application/json');
    
    try {
        $db = get_db($db_path);
        $stmt = $db->prepare('SELECT tracking_id, opened_at, user_agent, ip_address FROM open_events WHERE opened_at > :since ORDER BY opened_at ASC');
        $stmt->bindValue(':since', $since, SQLITE3_TEXT);
        $result = $stmt->execute();
        
        $opens = [];
        while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
            $tid = $row['tracking_id'];
            if (!isset($opens[$tid])) {
                $opens[$tid] = [
                    'first_opened_at' => $row['opened_at'],
                    'total_opens' => 0,
                    'user_agent' => $row['user_agent'] ?: '',
                    'ip_address' => $row['ip_address'] ?: ''
                ];
            }
            $opens[$tid]['total_opens']++;
        }
        $db->close();
        
        echo json_encode(['opens' => $opens, 'count' => count($opens)]);
    } catch (Exception $e) {
        echo json_encode(['opens' => (object)[], 'count' => 0, 'error' => $e->getMessage()]);
    }
    exit;
}
?>
