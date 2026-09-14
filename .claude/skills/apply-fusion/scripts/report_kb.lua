-- report_kb.lua -- per-item motion readback for the apply-fusion skill.
--
-- Writes one TSV row per video-track-1 item to REPORT_PATH:
--   index, name, start, duration, comp count, KB tool present,
--   Size at frame 0 / mid / last, Pivot x,y, Center x,y at frame 0 and last.
-- scripts/check_kb.py compares the report with the spec. A readback, not
-- proof: render a range afterwards.
--
-- Run like apply_baseline.lua: copy into `script_plugin path Edit` with
-- REPORT_PATH set, then `script_plugin execute`.

local REPORT_PATH = os.getenv("KB_REPORT_PATH") or [[C:\Users\<user>\Videos\<slug>-<fps>\kb-report.tsv]]

local function num(v)
  if type(v) == "number" then return string.format("%.4f", v) end
  return ""
end

local function xy(v)
  if type(v) == "table" then return num(v[1]) .. "\t" .. num(v[2]) end
  return "\t"
end

local resolve = Resolve()
local tl = resolve:GetProjectManager():GetCurrentProject():GetCurrentTimeline()
local out = io.open(REPORT_PATH, "w")
out:write("index\tname\tstart\tframes\tcomps\tkb\tsize0\tsize_mid\tsize_last\tpivot_x\tpivot_y\tcenter0_x\tcenter0_y\tcenter_last_x\tcenter_last_y\n")
for i, item in ipairs(tl:GetItemListInTrack("video", 1)) do
  local n = item:GetDuration()
  local comps = item:GetFusionCompCount() or 0
  local row = { tostring(i), item:GetName() or "", tostring(item:GetStart()), tostring(n), tostring(comps) }
  local xf = comps > 0 and item:GetFusionCompByIndex(1):FindTool("KB") or nil
  if xf then
    local last = n - 1
    row[#row + 1] = "1"
    row[#row + 1] = num(xf.Size[0])
    row[#row + 1] = num(xf.Size[math.floor(last / 2)])
    row[#row + 1] = num(xf.Size[last])
    row[#row + 1] = xy(xf.Pivot[0])
    row[#row + 1] = xy(xf.Center[0])
    row[#row + 1] = xy(xf.Center[last])
  else
    row[#row + 1] = "0"
  end
  out:write(table.concat(row, "\t") .. "\n")
end
out:close()
print("report_kb: wrote " .. REPORT_PATH)
