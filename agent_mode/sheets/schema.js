/**
 * Google Sheets structure definitions for CHERP crew spreadsheets.
 * Defines headers, column widths, formatting, and data validation per tab.
 */

// Tab definitions — order matters (tab index in spreadsheet)
const TABS = [
  {
    name: 'Roster',
    table: 'user_profiles',
    editable: true,
    idColumn: 'id',
    teamFilter: 'team_code',
    headers: [
      { key: 'id',               label: 'ID',               width: 80,  hidden: true },
      { key: 'display_name',     label: 'Name',             width: 180 },
      { key: 'role',             label: 'Role',             width: 120, validation: ['apprentice','worker','foreman','general_foreman','superintendent'] },
      { key: 'phone_number',     label: 'Phone',            width: 140 },
      { key: 'emergency_contact',label: 'Emergency Contact',width: 160 },
      { key: 'emergency_phone',  label: 'Emergency Phone',  width: 140 },
      { key: 'username',         label: 'Username',         width: 120 },
      { key: 'company_name',     label: 'Company',          width: 160 },
      { key: 'created_at',       label: 'Added',            width: 120, format: 'date' }
    ],
    headerColor: { red: 0.15, green: 0.25, blue: 0.45 }
  },
  {
    name: 'Timecards',
    table: 'crew_timecards',
    editable: true,
    idColumn: 'id',
    teamFilter: 'team_code',
    headers: [
      { key: 'id',        label: 'ID',         width: 80,  hidden: true },
      { key: 'user_name', label: 'Worker',      width: 160 },
      { key: 'date',      label: 'Date',        width: 110, format: 'date' },
      { key: 'clock_in',  label: 'Clock In',    width: 140, format: 'datetime' },
      { key: 'clock_out', label: 'Clock Out',   width: 140, format: 'datetime' },
      { key: 'hours',     label: 'Hours',       width: 80,  format: 'number' },
      { key: 'role',      label: 'Role',        width: 120 },
      { key: 'status',    label: 'Status',      width: 100, validation: ['active','completed'] },
      { key: 'notes',     label: 'Notes',       width: 200 }
    ],
    headerColor: { red: 0.12, green: 0.35, blue: 0.22 },
    sortBy: 'date',
    sortDesc: true
  },
  {
    name: 'Tasks',
    table: 'crew_tasks',
    editable: true,
    idColumn: 'id',
    teamFilter: 'team_code',
    headers: [
      { key: 'id',          label: 'ID',          width: 80,  hidden: true },
      { key: 'text',        label: 'Task',         width: 280 },
      { key: 'assigned_to', label: 'Assigned To',  width: 140 },
      { key: 'priority',    label: 'Priority',     width: 100, validation: ['normal','urgent'] },
      { key: 'done',        label: 'Done',         width: 70,  format: 'boolean' },
      { key: 'work_type',   label: 'Type',         width: 120 },
      { key: 'progress',    label: 'Progress %',   width: 90,  format: 'number' },
      { key: 'due_date',    label: 'Due Date',     width: 110, format: 'date' },
      { key: 'created_by',  label: 'Created By',   width: 120 },
      { key: 'created_at',  label: 'Created',      width: 120, format: 'date' }
    ],
    headerColor: { red: 0.4, green: 0.25, blue: 0.1 }
  },
  {
    name: 'MROs',
    table: 'crew_mros',
    editable: true,
    idColumn: 'id',
    teamFilter: 'team_code',
    headers: [
      { key: 'id',            label: 'ID',           width: 80,  hidden: true },
      { key: 'mro_num',       label: 'MRO #',        width: 80 },
      { key: 'description',   label: 'Description',   width: 260 },
      { key: 'requested_by',  label: 'Requested By',  width: 140 },
      { key: 'system',        label: 'System',        width: 120 },
      { key: 'status',        label: 'Status',        width: 110, validation: ['Processing','Partial','Fulfilled','Cancelled'] },
      { key: 'date_needed',   label: 'Date Needed',   width: 110, format: 'date' },
      { key: 'date_ordered',  label: 'Date Ordered',  width: 110, format: 'date' },
      { key: 'notes',         label: 'Notes',         width: 200 }
    ],
    headerColor: { red: 0.35, green: 0.15, blue: 0.35 }
  },
  {
    name: 'Incidents',
    table: 'crew_incidents',
    editable: false,
    idColumn: 'id',
    teamFilter: 'team_code',
    headers: [
      { key: 'id',               label: 'ID',              width: 80,  hidden: true },
      { key: 'incident_type',    label: 'Type',             width: 130 },
      { key: 'severity',         label: 'Severity',         width: 100 },
      { key: 'description',      label: 'Description',      width: 300 },
      { key: 'location',         label: 'Location',         width: 150 },
      { key: 'date',             label: 'Date',             width: 110, format: 'date' },
      { key: 'reported_by',      label: 'Reported By',      width: 130 },
      { key: 'corrective_action',label: 'Corrective Action',width: 250 },
      { key: 'status',           label: 'Status',           width: 110 }
    ],
    headerColor: { red: 0.5, green: 0.1, blue: 0.1 }
  },
  {
    name: 'Certifications',
    table: 'worker_certifications',
    editable: false,
    idColumn: 'id',
    teamFilter: null,  // Joined via user_profiles.team_code
    headers: [
      { key: 'id',          label: 'ID',          width: 80,  hidden: true },
      { key: 'user_name',   label: 'Worker',       width: 160 },
      { key: 'cert_name',   label: 'Certificate',  width: 200 },
      { key: 'cert_type',   label: 'Type',         width: 110 },
      { key: 'cert_number', label: 'Number',       width: 130 },
      { key: 'issue_date',  label: 'Issued',       width: 110, format: 'date' },
      { key: 'expiry_date', label: 'Expires',      width: 110, format: 'date' },
      { key: 'status',      label: 'Status',       width: 100 },
      { key: 'approved_by', label: 'Approved By',  width: 130 }
    ],
    headerColor: { red: 0.1, green: 0.3, blue: 0.45 }
  },
  {
    name: 'JSAs',
    table: 'crew_jsa',
    editable: false,
    idColumn: 'id',
    teamFilter: 'team_code',
    headers: [
      { key: 'id',               label: 'ID',                width: 80,  hidden: true },
      { key: 'date',             label: 'Date',              width: 110, format: 'date' },
      { key: 'job_site',         label: 'Job Site',          width: 180 },
      { key: 'task_description', label: 'Task',              width: 260 },
      { key: 'status',           label: 'Status',            width: 100 },
      { key: 'created_by',       label: 'Created By',        width: 130 },
      { key: 'emergency_procedures', label: 'Emergency Procedures', width: 250 },
      { key: 'created_at',       label: 'Created',           width: 120, format: 'date' }
    ],
    headerColor: { red: 0.45, green: 0.3, blue: 0.1 }
  },
  {
    name: 'Crew Info',
    table: 'team_codes',
    editable: false,
    idColumn: 'code',
    teamFilter: 'code',
    headers: [
      { key: 'code',          label: 'Team Code',   width: 110 },
      { key: 'crew_name',     label: 'Crew Name',   width: 200 },
      { key: 'company_name',  label: 'Company',     width: 200 },
      { key: 'foreman_name',  label: 'Foreman',     width: 160 },
      { key: 'foreman_phone', label: 'Foreman Phone',width: 140 },
      { key: 'active',        label: 'Active',      width: 80,  format: 'boolean' },
      { key: 'created_at',    label: 'Created',     width: 120, format: 'date' }
    ],
    headerColor: { red: 0.2, green: 0.2, blue: 0.3 }
  }
];

/** Get tab definition by name */
function getTab(name) {
  return TABS.find(t => t.name === name);
}

/** Get all editable tabs */
function getEditableTabs() {
  return TABS.filter(t => t.editable);
}

/** Get header labels for a tab */
function getHeaders(tabName) {
  const tab = getTab(tabName);
  return tab ? tab.headers.map(h => h.label) : [];
}

/** Get column keys for a tab (for mapping data) */
function getKeys(tabName) {
  const tab = getTab(tabName);
  return tab ? tab.headers.map(h => h.key) : [];
}

/**
 * Build Google Sheets API formatting requests for a tab.
 * Returns array of request objects for batchUpdate.
 */
function buildFormatRequests(tab, sheetId) {
  const requests = [];

  // Freeze header row
  requests.push({
    updateSheetProperties: {
      properties: { sheetId, gridProperties: { frozenRowCount: 1 } },
      fields: 'gridProperties.frozenRowCount'
    }
  });

  // Header row background color
  requests.push({
    repeatCell: {
      range: { sheetId, startRowIndex: 0, endRowIndex: 1 },
      cell: {
        userEnteredFormat: {
          backgroundColor: tab.headerColor,
          textFormat: { bold: true, foregroundColor: { red: 1, green: 1, blue: 1 } }
        }
      },
      fields: 'userEnteredFormat(backgroundColor,textFormat)'
    }
  });

  // Column widths
  tab.headers.forEach((h, i) => {
    requests.push({
      updateDimensionProperties: {
        range: { sheetId, dimension: 'COLUMNS', startIndex: i, endIndex: i + 1 },
        properties: { pixelSize: h.width },
        fields: 'pixelSize'
      }
    });
  });

  // Hide ID columns
  tab.headers.forEach((h, i) => {
    if (h.hidden) {
      requests.push({
        updateDimensionProperties: {
          range: { sheetId, dimension: 'COLUMNS', startIndex: i, endIndex: i + 1 },
          properties: { hiddenByUser: true },
          fields: 'hiddenByUser'
        }
      });
    }
  });

  // Dropdown validation for columns with validation arrays
  tab.headers.forEach((h, i) => {
    if (h.validation) {
      requests.push({
        setDataValidation: {
          range: { sheetId, startRowIndex: 1, startColumnIndex: i, endColumnIndex: i + 1 },
          rule: {
            condition: {
              type: 'ONE_OF_LIST',
              values: h.validation.map(v => ({ userEnteredValue: v }))
            },
            showCustomUi: true,
            strict: false
          }
        }
      });
    }
  });

  // Read-only tab protection
  if (!tab.editable) {
    requests.push({
      addProtectedRange: {
        protectedRange: {
          range: { sheetId },
          description: `${tab.name} — read only (synced from CHERP)`,
          warningOnly: true
        }
      }
    });
  }

  return requests;
}

module.exports = { TABS, getTab, getEditableTabs, getHeaders, getKeys, buildFormatRequests };
