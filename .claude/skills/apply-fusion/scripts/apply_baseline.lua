-- apply_baseline.lua -- Baseline-zoom batch for the apply-fusion skill.
--
-- Check every run with report_kb.lua + check_kb.py, then a rendered range
-- measured by check_render.py.
--
-- What it does: for every record in a JSON spec, finds the timeline item on
-- video track 1 (by scene_id prefix of the clip name, or by 1-based
-- item_index), reuses the item's first Fusion comp (or adds one), wires
-- MediaIn1 -> KB (Transform) -> MediaOut1, sets the zoom pivot, and attaches
-- a BezierSpline to Size with two keyframes (frame 0 and frames - 1).
--
-- How to run: set SPEC_PATH below (or the KB_SPEC_PATH user env var), then
--   script_plugin install  (language "lua", category "Edit", overwrite true,
--                           source = this file)
--   script_plugin execute  (same name / category / language)
-- execute returns success:false because fusion.RunScript is non-blocking --
-- the script still runs. print() output reaches only Workspace -> Console
-- (Lua tab); capture that window with scripts/capture-window.ps1 -Title Resolve.
--
-- Spec shape (flat records only -- the parser below cannot see nested objects):
-- {
--   "expected": 2,
--   "scenes": [
--     {"scene_id": "001_slug", "size_start": 1.0, "size_end": 1.15,
--      "center_x": 0.5, "center_y": 0.5, "ease": "EI", "frames": 120},
--     {"item_index": 2, "size_start": 1.15, "size_end": 1.0,
--      "center_x": 0.5, "center_y": 0.5, "ease": "L", "frames": 96}
--   ]
-- }
-- center_x / center_y are the zoom pivot as TOP-LEFT image fractions
-- (the plan's convention); this script sets Transform.Pivot and does the
-- Fusion Y-flip (fusion_y = 1 - y). ease: L | EI | EO.
-- A pan record adds "pan": 1 and cx0, cy0, cx1, cy1 (Center start and end,
-- top-left): Size holds at size_start and Center is keyframed instead.
-- scripts/plan_to_spec.py writes the spec from ken-burns-plan.md.

local SPEC_PATH = os.getenv("KB_SPEC_PATH") or [[C:\Users\<user>\Videos\<slug>-<fps>\ken-burns-spec.json]]
local TOOL_NAME = "KB"

-- ---------------------------------------------------------------- spec ----

local function read_file(path)
  local f = io.open(path, "r")
  if not f then return nil end
  local s = f:read("*a")
  f:close()
  return s
end

local function field_num(rec, key)
  local v = rec:match('"' .. key .. '"%s*:%s*(-?[%d%.]+)')
  return v and tonumber(v) or nil
end

local function field_str(rec, key)
  return rec:match('"' .. key .. '"%s*:%s*"([^"]*)"')
end

local function parse_spec(raw)
  -- TRAP: raw:gmatch("%b{}") over the whole document matches the OUTER
  -- object first and yields exactly one bogus record assembled from the
  -- first value of every key. It then reports "1 scene" and applies
  -- nothing useful. Narrow to the scenes array before matching records.
  local arr = raw:match('"scenes"%s*:%s*(%b[])')
  if not arr then return nil, 'no "scenes" array found' end
  local expected = tonumber(raw:match('"expected"%s*:%s*(%d+)') or "0")
  local scenes = {}
  for rec in arr:gmatch("%b{}") do
    scenes[#scenes + 1] = {
      scene_id   = field_str(rec, "scene_id"),
      item_index = field_num(rec, "item_index"),
      size_start = field_num(rec, "size_start") or 1.0,
      size_end   = field_num(rec, "size_end") or 1.15,
      center_x   = field_num(rec, "center_x") or 0.5,
      center_y   = field_num(rec, "center_y") or 0.5,
      ease       = field_str(rec, "ease") or "L",
      frames     = field_num(rec, "frames"),
      pan        = field_num(rec, "pan"),
      cx0 = field_num(rec, "cx0"), cy0 = field_num(rec, "cy0"),
      cx1 = field_num(rec, "cx1"), cy1 = field_num(rec, "cy1"),
    }
  end
  return scenes, nil, expected
end

-- ------------------------------------------------------------- keyframes --

-- Two-key spline from (t0, v0) to (t1, v1). Handles are {time, value}
-- OFFSETS from their own key, not absolute points: absolute values read as
-- offsets throw the curve far past v1 (Size 1.87 on a 1.00 -> 1.15 zoom).
-- EI = flat start, straight arrival (building); EO = straight start, flat
-- arrival (release); L = linear.
local function make_keys(t0, v0, t1, v1, ease)
  local dt, dv = t1 - t0, v1 - v0
  if ease == "EI" then
    return {
      [t0] = { v0, RH = { dt * 0.6, 0 } },
      [t1] = { v1, LH = { -dt / 3, -dv / 3 } },
    }
  elseif ease == "EO" then
    return {
      [t0] = { v0, RH = { dt / 3, dv / 3 } },
      [t1] = { v1, LH = { -dt * 0.6, 0 } },
    }
  end
  return {
    [t0] = { v0, RH = { dt / 3, dv / 3 } },
    [t1] = { v1, LH = { -dt / 3, -dv / 3 } },
  }
end

-- ------------------------------------------------------------------ main --

local function find_item(items, spec)
  if spec.item_index then return items[spec.item_index], spec.item_index end
  if not spec.scene_id then return nil end
  for i, it in ipairs(items) do
    local n = it:GetName() or ""
    if n == spec.scene_id or n:sub(1, #spec.scene_id + 1) == spec.scene_id .. "." then
      return it, i
    end
  end
  return nil
end

local function apply_one(item, spec)
  -- Reuse the first comp: a second comp on the same item is the multi-comp
  -- trap (the GUI shows whichever a human last opened, not the API's).
  local comp
  if item:GetFusionCompCount() >= 1 then
    comp = item:GetFusionCompByIndex(1)
  else
    comp = item:AddFusionComp()
  end
  if not comp then return false, "no comp" end

  -- StartUndo/EndUndo, never comp:Lock() -- Lock() is the silent
  -- render-failure trap (keyframes visible live, absent from the render).
  comp:StartUndo("apply_baseline")
  local ok, err = pcall(function()
    local mi = comp:FindTool("MediaIn1")
    local mo = comp:FindTool("MediaOut1")
    if not (mi and mo) then error("MediaIn1/MediaOut1 missing") end

    local xf = comp:FindTool(TOOL_NAME)
    if not xf then
      xf = comp:AddTool("Transform", -32768, -32768)
      xf:SetAttrs({ TOOLS_Name = TOOL_NAME })
    end
    -- Both connections. Missing the first leaves the tool keyframing fine
    -- while the viewer says "No frame available for MediaOut1".
    xf.Input = mi.Output
    mo.Input = xf.Output

    -- Pivot, not Center: Center moves the image; Pivot is what Size scales
    -- around. Y-flip from the plan's top-left fractions.
    xf.Pivot = { spec.center_x, 1 - spec.center_y }

    local last = math.max(1, math.floor(spec.frames + 0.5) - 1)
    if spec.pan then
      -- Pan: static Size for headroom, Center animated on an XYPath from
      -- (cx0, cy0) to (cx1, cy1), top-left fractions flipped to Fusion's Y.
      xf.Size = spec.size_start
      xf.Center = comp:XYPath()
      xf.Center[0] = { spec.cx0, 1 - spec.cy0 }
      xf.Center[last] = { spec.cx1, 1 - spec.cy1 }
    else
      xf.Size = comp:BezierSpline()
      local spline = xf.Size:GetConnectedOutput():GetTool()
      spline:SetKeyFrames(make_keys(0, spec.size_start, last, spec.size_end, spec.ease), true)
    end
  end)
  comp:EndUndo(ok and true or false)
  return ok, err
end

local function main()
  local resolve = Resolve()
  local project = resolve and resolve:GetProjectManager():GetCurrentProject()
  local tl = project and project:GetCurrentTimeline()
  if not tl then print("apply_baseline: no current timeline") return end

  local raw = read_file(SPEC_PATH)
  if not raw then print("apply_baseline: cannot read spec " .. SPEC_PATH) return end
  local scenes, perr, expected = parse_spec(raw)
  if not scenes then print("apply_baseline: " .. perr) return end
  print(string.format("apply_baseline: spec loaded: %d scenes (expected %d)", #scenes, expected or 0))

  -- COUNT GUARD: a half-applied motion pass is worse than a clean abort.
  -- "expected" in the spec is written by whoever generated it; anything
  -- short of it means the parse went wrong (see the %b{} trap above).
  if expected and expected > 0 and #scenes < expected then
    print("apply_baseline: ABORT -- parsed fewer scenes than expected, nothing applied")
    return
  end
  if #scenes == 0 then print("apply_baseline: ABORT -- no scenes parsed") return end

  local items = tl:GetItemListInTrack("video", 1)
  if not items or #items == 0 then print("apply_baseline: video track 1 is empty") return end

  local applied, skipped, failed = 0, 0, 0
  for n, spec in ipairs(scenes) do
    local item, idx = find_item(items, spec)
    local label = spec.scene_id or ("item_index " .. tostring(spec.item_index))
    if not item then
      skipped = skipped + 1
      print(string.format("  [%d] %s: no matching timeline item, skipped", n, label))
    elseif not spec.frames or spec.frames < 2 then
      skipped = skipped + 1
      print(string.format("  [%d] %s: frames missing or < 2, skipped", n, label))
    else
      local ok, err = apply_one(item, spec)
      if ok then
        applied = applied + 1
        if spec.pan then
          print(string.format("  [%d] %s (item %d): Pan Center (%.2f,%.2f) -> (%.2f,%.2f) at Size %.2f over %d frames",
            n, label, idx, spec.cx0, spec.cy0, spec.cx1, spec.cy1, spec.size_start, spec.frames))
        else
          print(string.format("  [%d] %s (item %d): Size %.3f -> %.3f %s over %d frames",
            n, label, idx, spec.size_start, spec.size_end, spec.ease, spec.frames))
        end
      else
        failed = failed + 1
        print(string.format("  [%d] %s (item %d): FAILED %s", n, label, idx, tostring(err)))
      end
    end
  end
  print(string.format("apply_baseline: done -- applied=%d skipped=%d failed=%d", applied, skipped, failed))
end

main()
