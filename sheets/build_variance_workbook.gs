/**
 * Ads P&L — weekly variance analysis workbook (Google Sheets, Apps Script).
 * ALL DATA IS SIMULATED. Not Swiggy data.
 *
 * Builds the workbook from scratch in the spreadsheet it is bound to:
 *   - data tabs that IMPORTDATA the CSVs the GitHub Actions pipeline publishes every Monday
 *     (the same dbt mart rows the dashboard reads, so numbers always agree)
 *   - "Variance": week + product selectors, then formulas only:
 *       1. scorecard (this week vs last week vs 4-week avg)
 *       2. revenue bridge: price-volume decomposition requests x fill x CTR x price
 *       3. variance by product   4. CTR mix-vs-rate decomposition   5. variance by zone
 *   - "Pivot": zone x week revenue pivot table
 * Run buildAdsPnlWorkbook() once. Works bound to the sheet (Extensions > Apps Script) or as a
 * standalone script: set SPREADSHEET_ID to the target spreadsheet's id.
 */
const SPREADSHEET_ID = '1e-FrVWl55V_LbD7jN3XmZAy-vfgXMzr141zgAF-ubI8';
const BASE_URL = 'http://vivekbuilds.me/swiggy-ads-pnl/data/';
const DATA_TABS = ['kpi_weekly', 'kpi_cube', 'revenue_bridge', 'zones', 'categories', 'top_advertisers',
                   'kpi_weekly_wide', 'advertiser_weekly_summary', 'movers'];
const INR = '[$₹]#,##0';
const PCT = '0.0%';
const PCT2 = '0.00%';

function buildAdsPnlWorkbook() {
  const ss = SPREADSHEET_ID ? SpreadsheetApp.openById(SPREADSHEET_ID) : SpreadsheetApp.getActive();
  ss.rename('Ads P&L — weekly variance analysis (simulated data)');

  // ---- data tabs (live) -------------------------------------------------------------------
  DATA_TABS.forEach(function (name) {
    const sh = ss.getSheetByName(name) || ss.insertSheet(name);
    sh.clear();
    sh.getRange('A1').setFormula('=IMPORTDATA("' + BASE_URL + name + '.csv")');
    sh.setTabColor('#9aa0a6');
    sh.setFrozenRows(1);
  });
  SpreadsheetApp.flush();

  buildVariance_(ss);
  buildPivot_(ss);
  buildReadme_(ss);

  ['Sheet1'].forEach(function (n) { const s = ss.getSheetByName(n); if (s && ss.getSheets().length > 1) ss.deleteSheet(s); });
  const v = ss.getSheetByName('Variance');
  ss.setActiveSheet(v);
  ss.moveActiveSheet(1);
  Logger.log('Built: ' + ss.getUrl());
}

function buildVariance_(ss) {
  const v = ss.getSheetByName('Variance') || ss.insertSheet('Variance', 0);
  v.clear(); v.clearConditionalFormatRules();
  v.getCharts().forEach(function (c) { v.removeChart(c); });
  v.setHiddenGridlines(true);
  v.setColumnWidth(1, 230);
  for (let c = 2; c <= 8; c++) v.setColumnWidth(c, 115);

  v.getRange('A1').setValue('Weekly variance analysis — Ads P&L').setFontSize(16).setFontWeight('bold');
  v.getRange('A2').setValue('Simulated data — not Swiggy data. Every number is read from the dbt marts published weekly by the pipeline (data tabs refresh automatically).')
    .setFontColor('#5f6368');

  // selectors
  v.getRange('A4:A6').setValues([['Week'], ['Product'], ['Compared with week']]).setFontWeight('bold');
  v.getRange('B4').setValue(26);
  v.getRange('B4').setDataValidation(SpreadsheetApp.newDataValidation().requireNumberBetween(2, 26).setAllowInvalid(false).build());
  v.getRange('B5').setValue('all');
  v.getRange('B5').setDataValidation(SpreadsheetApp.newDataValidation()
    .requireValueInList(['all', 'food_listing', 'instamart_search', 'home_banner'], true).build());
  v.getRange('B6').setFormula('=B4-1');
  v.getRange('B4:B5').setBackground('#e8f0fe').setFontWeight('bold');
  v.getRange('C4').setValue('← pick a week (2–26) and a product').setFontColor('#5f6368');

  // ---- 1. scorecard ------------------------------------------------------------------------
  let r = 8;
  section_(v, r, '1. Scorecard — this week vs last week vs 4-week average');
  header_(v, r + 1, ['Metric', 'This week', 'Last week', 'Δ', 'Δ %', '4-wk avg', 'vs 4-wk', 'key']);
  const metrics = [
    ['Ad revenue (gross)', 'ad_revenue', INR], ['CPM (eCPM)', 'ecpm', '[$₹]#,##0.00'], ['CTR', 'ctr', PCT2],
    ['Fill rate', 'fill_rate', PCT], ['Active advertisers', 'active_advertisers', '#,##0'], ['ROAS', 'roas', '0.00"x"'],
    ['Ad requests', 'ad_requests', '#,##0'], ['Clicks', 'clicks', '#,##0'], ['CPC', 'cpc', '[$₹]#,##0.00'],
    ['Conversion rate', 'cvr', PCT], ['Bid density', 'bid_density', '0.0'], ['Top-10 concentration', 'top10_concentration', PCT]];
  const f = function (col, row) {
    return '=IF(COUNTIFS(kpi_weekly!$A:$A,$B$4,kpi_weekly!$C:$C,$B$5,kpi_weekly!$D:$D,$H' + row + ')=0,"",' +
           'SUMIFS(kpi_weekly!$' + col + ':$' + col + ',kpi_weekly!$A:$A,$B$4,kpi_weekly!$C:$C,$B$5,kpi_weekly!$D:$D,$H' + row + '))';
  };
  metrics.forEach(function (m, i) {
    const row = r + 2 + i;
    v.getRange(row, 1).setValue(m[0]);
    v.getRange(row, 8).setValue(m[1]).setFontColor('#bdc1c6');
    v.getRange(row, 2, 1, 6).setFormulas([[f('F', row), f('G', row), '=IFERROR(B' + row + '-C' + row + ',"")',
      '=IFERROR(B' + row + '/C' + row + '-1,"")', f('I', row), '=IFERROR(B' + row + '/F' + row + '-1,"")']]);
    v.getRange(row, 2, 1, 2).setNumberFormat(m[2]);
    v.getRange(row, 4).setNumberFormat(m[2] === PCT || m[2] === PCT2 ? '+0.00" pp";-0.00" pp"' : m[2]);
    if (m[2] === PCT || m[2] === PCT2) v.getRange(row, 4).setFormula('=IFERROR((B' + row + '-C' + row + ')*100,"")');
    v.getRange(row, 6).setNumberFormat(m[2]);
    v.getRange(row, 5).setNumberFormat('+0.0%;-0.0%');
    v.getRange(row, 7).setNumberFormat('+0.0%;-0.0%');
  });
  const scEnd = r + 1 + metrics.length;
  redGreen_(v, 'E' + (r + 2) + ':E' + scEnd);
  redGreen_(v, 'G' + (r + 2) + ':G' + scEnd);

  // ---- 2. revenue bridge -------------------------------------------------------------------
  r = scEnd + 3;
  section_(v, r, '2. Revenue bridge — price-volume decomposition (revenue = requests × fill × CTR × price)');
  header_(v, r + 1, ['Step', 'INR', 'Share of change']);
  const b = function (col) {
    return '=SUMIFS(revenue_bridge!$' + col + ':$' + col + ',revenue_bridge!$A:$A,$B$4,revenue_bridge!$B:$B,$B$5)';
  };
  const steps = [['Revenue, last week', b('C')], ['  Ad requests (volume)', b('F')], ['  Fill rate', b('G')],
    ['  CTR', b('H')], ['  Price (CPC / eCPM)', b('I')], ['Revenue, this week', b('D')]];
  steps.forEach(function (s, i) {
    const row = r + 2 + i;
    v.getRange(row, 1).setValue(s[0]);
    v.getRange(row, 2).setFormula(s[1]).setNumberFormat(INR);
    if (i >= 1 && i <= 4) v.getRange(row, 3).setFormula('=IFERROR(B' + row + '/(B' + (r + 7) + '-B' + (r + 2) + '),"")').setNumberFormat(PCT);
  });
  v.getRange(r + 8, 1).setValue('Check: effects − change (should be 0)').setFontColor('#5f6368');
  v.getRange(r + 8, 2).setFormula('=ROUND(SUM(B' + (r + 3) + ':B' + (r + 6) + ')-(B' + (r + 7) + '-B' + (r + 2) + '),2)').setNumberFormat(INR);
  redGreen_(v, 'B' + (r + 3) + ':B' + (r + 6));
  const bridgeStart = r + 2;
  const chart = v.newChart().asColumnChart().addRange(v.getRange('A' + (r + 3) + ':B' + (r + 6)))
    .setPosition(r, 5, 0, 0).setOption('title', 'Revenue change by driver (INR)').setOption('legend', { position: 'none' })
    .setOption('colors', ['#1a73e8']).setOption('width', 520).setOption('height', 240).build();
  v.insertChart(chart);

  // ---- 3. variance by product --------------------------------------------------------------
  r = r + 11;
  section_(v, r, '3. Variance by product (gross ad revenue)');
  header_(v, r + 1, ['Product', 'This week', 'Last week', 'Δ', 'Δ %', 'Share of total Δ']);
  const cube = function (week, surf) {
    return 'SUMIFS(kpi_cube!$E:$E,kpi_cube!$A:$A,' + week + ',kpi_cube!$B:$B,"' + surf + '",kpi_cube!$C:$C,"all",kpi_cube!$D:$D,"all")';
  };
  const prods = ['food_listing', 'instamart_search', 'home_banner', 'all'];
  prods.forEach(function (p, i) {
    const row = r + 2 + i;
    v.getRange(row, 1).setValue(p === 'all' ? 'Total' : p);
    v.getRange(row, 2, 1, 5).setFormulas([['=' + cube('$B$4', p), '=' + cube('$B$6', p), '=B' + row + '-C' + row,
      '=IFERROR(B' + row + '/C' + row + '-1,"")', '=IFERROR(D' + row + '/$D$' + (r + 5) + ',"")']]);
    v.getRange(row, 2, 1, 3).setNumberFormat(INR);
    v.getRange(row, 5).setNumberFormat('+0.0%;-0.0%');
    v.getRange(row, 6).setNumberFormat(PCT);
  });
  v.getRange(r + 5, 1, 1, 6).setFontWeight('bold');
  redGreen_(v, 'D' + (r + 2) + ':D' + (r + 4));

  // ---- 4. mix vs rate ----------------------------------------------------------------------
  r = r + 8;
  section_(v, r, '4. Why did CTR move? Mix vs rate across products');
  v.getRange(r + 1, 1).setValue('ΔCTR = Σ (s¹ − s⁰)·CTR⁰  [mix]  +  Σ s¹·(CTR¹ − CTR⁰)  [rate],  s = share of impressions').setFontColor('#5f6368');
  header_(v, r + 2, ['Product', 'Imp. share, last wk', 'Imp. share, this wk', 'CTR, last wk', 'CTR, this wk', 'Mix effect', 'Rate effect']);
  const cubeCol = function (col, week, surf) {
    return 'SUMIFS(kpi_cube!$' + col + ':$' + col + ',kpi_cube!$A:$A,' + week + ',kpi_cube!$B:$B,"' + surf + '",kpi_cube!$C:$C,"all",kpi_cube!$D:$D,"all")';
  };
  ['food_listing', 'instamart_search', 'home_banner'].forEach(function (p, i) {
    const row = r + 3 + i;
    v.getRange(row, 1).setValue(p);
    v.getRange(row, 2, 1, 6).setFormulas([[
      '=' + cubeCol('G', '$B$6', p) + '/' + cubeCol('G', '$B$6', 'all'),
      '=' + cubeCol('G', '$B$4', p) + '/' + cubeCol('G', '$B$4', 'all'),
      '=' + cubeCol('H', '$B$6', p) + '/' + cubeCol('G', '$B$6', p),
      '=' + cubeCol('H', '$B$4', p) + '/' + cubeCol('G', '$B$4', p),
      '=(C' + row + '-B' + row + ')*D' + row,
      '=C' + row + '*(E' + row + '-D' + row + ')']]);
    v.getRange(row, 2, 1, 2).setNumberFormat(PCT);
    v.getRange(row, 4, 1, 2).setNumberFormat(PCT2);
    v.getRange(row, 6, 1, 2).setNumberFormat('+0.000" pp";-0.000" pp"');
    v.getRange(row, 6).setFormula('=(C' + row + '-B' + row + ')*D' + row + '*100');
    v.getRange(row, 7).setFormula('=C' + row + '*(E' + row + '-D' + row + ')*100');
  });
  const mt = r + 6;
  v.getRange(mt, 1).setValue('Total').setFontWeight('bold');
  v.getRange(mt, 6, 1, 2).setFormulas([['=SUM(F' + (r + 3) + ':F' + (r + 5) + ')', '=SUM(G' + (r + 3) + ':G' + (r + 5) + ')']])
    .setNumberFormat('+0.000" pp";-0.000" pp"').setFontWeight('bold');
  v.getRange(mt + 1, 1).setValue('Check: mix + rate − actual ΔCTR (pp)').setFontColor('#5f6368');
  v.getRange(mt + 1, 2).setFormula('=ROUND(F' + mt + '+G' + mt + '-(' + cubeCol('H', '$B$4', 'all') + '/' + cubeCol('G', '$B$4', 'all') +
    '-' + cubeCol('H', '$B$6', 'all') + '/' + cubeCol('G', '$B$6', 'all') + ')*100,6)');

  // ---- 5. variance by zone -----------------------------------------------------------------
  r = mt + 4;
  section_(v, r, '5. Variance by zone');
  header_(v, r + 1, ['Zone', 'Revenue this wk', 'Revenue last wk', 'Δ', 'Δ %', 'Share of total Δ', 'ROAS this wk']);
  const zones = ['Koramangala', 'Indiranagar', 'HSR Layout', 'Whitefield', 'Jayanagar', 'BTM Layout', 'Marathahalli',
    'Electronic City', 'JP Nagar', 'Bellandur', 'Malleshwaram', 'Hebbal', 'Yelahanka', 'Banashankari', 'Rajajinagar'];
  zones.forEach(function (z, i) {
    const row = r + 2 + i;
    const zs = function (col, wk) { return 'SUMIFS(zones!$' + col + ':$' + col + ',zones!$A:$A,' + wk + ',zones!$C:$C,$A' + row + ')'; };
    v.getRange(row, 1).setValue(z);
    v.getRange(row, 2, 1, 6).setFormulas([['=' + zs('F', '$B$4'), '=' + zs('F', '$B$6'), '=B' + row + '-C' + row,
      '=IFERROR(B' + row + '/C' + row + '-1,"")', '=IFERROR(D' + row + '/SUM($D$' + (r + 2) + ':$D$' + (r + 16) + '),"")', '=' + zs('N', '$B$4')]]);
    v.getRange(row, 2, 1, 3).setNumberFormat(INR);
    v.getRange(row, 5).setNumberFormat('+0.0%;-0.0%');
    v.getRange(row, 6).setNumberFormat(PCT);
    v.getRange(row, 7).setNumberFormat('0.00"x"');
  });
  v.getRange(r + 17, 1).setValue('Note: zone revenue covers zone-targeted spend; product filter does not apply to this section.').setFontColor('#5f6368');
  const rules = v.getConditionalFormatRules();
  rules.push(SpreadsheetApp.newConditionalFormatRule().setGradientMinpointWithValue('#f4c7c3', SpreadsheetApp.InterpolationType.NUMBER, '-0.1')
    .setGradientMidpointWithValue('#ffffff', SpreadsheetApp.InterpolationType.NUMBER, '0')
    .setGradientMaxpointWithValue('#b7e1cd', SpreadsheetApp.InterpolationType.NUMBER, '0.1')
    .setRanges([v.getRange('E' + (r + 2) + ':E' + (r + 16))]).build());
  v.setConditionalFormatRules(rules);

  // ---- trend helper + chart ----------------------------------------------------------------
  v.getRange('J8').setValue('Week').setFontWeight('bold');
  v.getRange('K8').setValue('Ad revenue').setFontWeight('bold');
  for (let w = 1; w <= 26; w++) {
    v.getRange(8 + w, 10).setValue(w);
    v.getRange(8 + w, 11).setFormula('=SUMIFS(kpi_weekly!$F:$F,kpi_weekly!$A:$A,J' + (8 + w) + ',kpi_weekly!$C:$C,$B$5,kpi_weekly!$D:$D,"ad_revenue")').setNumberFormat(INR);
  }
  v.getRange('J8:K34').setFontColor('#80868b');
  const trend = v.newChart().asLineChart().addRange(v.getRange('J8:K34')).setPosition(8, 13, 0, 0)
    .setOption('title', '26-week ad revenue (selected product)').setOption('legend', { position: 'none' })
    .setOption('colors', ['#1a73e8']).setOption('width', 560).setOption('height', 260).build();
  v.insertChart(trend);
  v.setFrozenRows(6);
}

function buildPivot_(ss) {
  const p = ss.getSheetByName('Pivot') || ss.insertSheet('Pivot');
  p.clear();
  p.getRange('A1').setValue('Pivot: gross ad revenue by zone × week (all products, all advertisers)').setFontWeight('bold');
  const src = ss.getSheetByName('kpi_cube').getRange('A1:U5000');
  const pt = p.getRange('A3').createPivotTable(src);
  pt.addRowGroup(3);                       // zone_id
  pt.addColumnGroup(1);                    // week_number
  pt.addPivotValue(5, SpreadsheetApp.PivotTableSummarizeFunction.SUM).setDisplayName('Revenue');
  pt.addFilter(2, SpreadsheetApp.newFilterCriteria().whenTextEqualTo('all').build());   // surface
  pt.addFilter(4, SpreadsheetApp.newFilterCriteria().whenTextEqualTo('all').build());   // advertiser_segment
  p.getRange('B4:AB30').setNumberFormat('[$₹]#,##0');
}

function buildReadme_(ss) {
  const r = ss.getSheetByName('README') || ss.insertSheet('README');
  r.clear();
  r.setColumnWidth(1, 900);
  r.getRange('A1:A12').setValues([
    ['Ads P&L — weekly variance analysis (SIMULATED DATA — not Swiggy data)'],
    [''],
    ['What this is: the spreadsheet half of the Ads P&L project. Variance tab = scorecard, price-volume revenue bridge,'],
    ['variance by product and zone, and a CTR mix-vs-rate decomposition — all formulas, driven by the week/product selectors.'],
    [''],
    ['Data: the grey tabs IMPORTDATA the CSVs that the GitHub Actions pipeline publishes every Monday from the dbt marts:'],
    [BASE_URL + '<table>.csv  — the same rows the dashboard reads, so the Sheet, dashboard and WBR memos always agree.'],
    [''],
    ['Dashboard: http://vivekbuilds.me/swiggy-ads-pnl/   ·   Code: https://github.com/Vivek-122005/swiggy-ads-pnl'],
    ['Rebuild: run buildAdsPnlWorkbook() from sheets/build_variance_workbook.gs in the repo (Apps Script).'],
    [''],
    ['Restaurant and brand names come from public Kaggle datasets; every ad metric attached to them is invented.']]);
  r.getRange('A1').setFontWeight('bold').setFontSize(14);
}

function section_(sh, row, title) {
  sh.getRange(row, 1).setValue(title).setFontWeight('bold').setFontSize(12).setFontColor('#174ea6');
}

function header_(sh, row, labels) {
  sh.getRange(row, 1, 1, labels.length).setValues([labels]).setFontWeight('bold')
    .setBackground('#f1f3f4').setBorder(false, false, true, false, false, false);
}

function redGreen_(sh, a1) {
  const rng = sh.getRange(a1);
  const rules = sh.getConditionalFormatRules();
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0).setFontColor('#c5221f').setRanges([rng]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0).setFontColor('#188038').setRanges([rng]).build());
  sh.setConditionalFormatRules(rules);
}
