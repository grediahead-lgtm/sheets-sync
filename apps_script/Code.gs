/**
 * Google Apps Script web app for sheets-sync: writes a table into a named sheet.
 * Setup: Extensions > Apps Script, paste this file, add Script property SYNC_SECRET,
 * Deploy > New deployment > Web app (Execute as: Me, access: Anyone), put the /exec URL in --webhook.
 * Request: {secret, sheet, mode: "replace"|"append", rows: [[...], ...]}
 */
function doPost(e) {
  var out = function (o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); };
  try {
    var d = JSON.parse(e.postData.contents);
    var secret = PropertiesService.getScriptProperties().getProperty('SYNC_SECRET');
    if (!secret || d.secret !== secret) return out({ ok: false, error: 'forbidden' });
    if (!/^[A-Za-z0-9_ -]{1,60}$/.test(d.sheet || '') || !d.rows || !d.rows.length || d.rows.length > 1000) return out({ ok: false, error: 'bad request' });
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName(d.sheet) || ss.insertSheet(d.sheet);
    if (d.mode === 'replace') sh.clearContents();
    var width = d.rows[0].length;
    var start = d.mode === 'replace' ? 1 : sh.getLastRow() + 1;
    var rows = d.rows.map(function (r) { return r.slice(0, width).map(function (c) { return String(c).slice(0, 1000); }); });
    sh.getRange(start, 1, rows.length, width).setValues(rows);
    return out({ ok: true });
  } catch (err) {
    return out({ ok: false, error: 'bad request' });
  }
}
