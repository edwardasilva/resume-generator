-- Reads resume.json and typesets it. Loaded by resume.tex.
local M = {}

-- Small JSON parser (objects, arrays, strings, numbers, true/false/null).
local function decode(s)
  local i = 1
  local function ws() i = s:find("[^ \t\r\n]", i) or #s + 1 end
  local function err(msg) error("resume.json: " .. msg .. " at character " .. i) end
  local value
  local function str()
    i = i + 1
    local out = {}
    while true do
      local c = s:sub(i, i)
      if c == "" then err("unterminated string") end
      if c == '"' then i = i + 1; return table.concat(out) end
      if c == "\\" then
        local e = s:sub(i + 1, i + 1)
        local map = { ['"'] = '"', ["\\"] = "\\", ["/"] = "/", b = "\b", f = "\f", n = "\n", r = "\r", t = "\t" }
        if map[e] then out[#out + 1] = map[e]; i = i + 2
        elseif e == "u" then
          local cp = tonumber(s:sub(i + 2, i + 5), 16) or err("bad \\u escape")
          i = i + 6
          if cp >= 0xD800 and cp <= 0xDBFF and s:sub(i, i + 1) == "\\u" then
            local lo = tonumber(s:sub(i + 2, i + 5), 16)
            cp = 0x10000 + (cp - 0xD800) * 0x400 + (lo - 0xDC00)
            i = i + 6
          end
          out[#out + 1] = utf8.char(cp)
        else err("bad escape") end
      else out[#out + 1] = c; i = i + 1 end
    end
  end
  function value()
    ws()
    local c = s:sub(i, i)
    if c == "{" then
      local t = {}; i = i + 1; ws()
      if s:sub(i, i) == "}" then i = i + 1; return t end
      while true do
        ws(); if s:sub(i, i) ~= '"' then err("expected key") end
        local k = str(); ws()
        if s:sub(i, i) ~= ":" then err("expected ':'") end
        i = i + 1; t[k] = value(); ws()
        local d = s:sub(i, i); i = i + 1
        if d == "}" then return t elseif d ~= "," then err("expected ',' or '}'") end
      end
    elseif c == "[" then
      local t = {}; i = i + 1; ws()
      if s:sub(i, i) == "]" then i = i + 1; return t end
      while true do
        t[#t + 1] = value(); ws()
        local d = s:sub(i, i); i = i + 1
        if d == "]" then return t elseif d ~= "," then err("expected ',' or ']'") end
      end
    elseif c == '"' then return str()
    elseif s:sub(i, i + 3) == "true" then i = i + 4; return true
    elseif s:sub(i, i + 4) == "false" then i = i + 5; return false
    elseif s:sub(i, i + 3) == "null" then i = i + 4; return nil
    else
      local num = s:match("^-?%d+%.?%d*[eE]?[-+]?%d*", i)
      if not num or num == "" then err("unexpected character") end
      i = i + #num; return tonumber(num)
    end
  end
  local v = value(); ws()
  if i <= #s then err("trailing data") end
  return v
end

-- Escape text once, character by character.
local ESC = {
  ["\\"] = "\\textbackslash{}", ["^"] = "\\textasciicircum{}", ["~"] = "\\textasciitilde{}",
  ["{"] = "\\{", ["}"] = "\\}", ["&"] = "\\&", ["%"] = "\\%", ["#"] = "\\#", ["_"] = "\\_", ["$"] = "\\$",
}
local function esc(s) return ((tostring(s or "")):gsub("[\\%^~{}&%%#_%$]", ESC)) end
local function url(s) return ((tostring(s)):gsub("[\\{}%%#~]", "\\%0")) end

local function blank(s) return s == nil or s == "" end
local function nonempty(list)
  local out = {}
  for _, x in ipairs(list or {}) do if not blank(x) then out[#out + 1] = x end end
  return out
end
local function visible(list)
  local out = {}
  for _, x in ipairs(list or {}) do if not x.hide then out[#out + 1] = x end end
  return out
end
local function joinesc(list, sep)
  local out = {}
  for _, x in ipairs(nonempty(list)) do out[#out + 1] = esc(x) end
  return table.concat(out, sep or ", ")
end
local function dates(a, b)
  a, b = a or "", b or ""
  if blank(b) and not blank(a) then b = "Present" end
  if blank(a) then return esc(b) end
  if a == b then return esc(a) end
  return esc(a) .. "--" .. esc(b)
end
local function display(u) return (u:gsub("^https?://", ""):gsub("^www%.", "")) end

-- Layout settings from the tightness factor RESUME_T (0 = loosest, 1 = tightest).
-- Spacing tightens first, then margins, then font size.
local function clamp(x) return math.max(0, math.min(1, x)) end
local t = clamp(tonumber(os.getenv("RESUME_T") or "0") or 0)
local s, m, f = clamp(t * 3), clamp(t * 3 - 1), clamp(t * 3 - 2)
M.font = 11 - f * 1             -- 11pt down to 10pt
M.margin = 0.75 - m * 0.35      -- 0.75in down to 0.4in
M.stretch = 1.15 - s * 0.08     -- line spacing 1.15 down to 1.07
M.gap = 1 - s * 0.6             -- section and item gaps scale 1 down to 0.4

function M.preamble()
  tex.print(string.format("\\def\\ResumeMargin{%.3fin}", M.margin))
end

function M.setup()
  local fs = M.font
  tex.print(string.format("\\fontsize{%.2fpt}{%.2fpt}\\selectfont", fs, fs * 1.2 * M.stretch))
  tex.print(string.format("\\setlength{\\secgap}{%.2fpt}\\setlength{\\itemgap}{%.2fpt}", 7 * M.gap, 3 * M.gap))
  tex.print(string.format("\\typeout{RESUME-SETTINGS font=%.2fpt margin=%.3fin linespacing=%.2f}", fs, M.margin, M.stretch))
end

local out = {}
local function emit(x) out[#out + 1] = x end
local function bullets(list)
  list = nonempty(list)
  if #list == 0 then return end
  emit("\\begin{itemize}")
  for _, b in ipairs(list) do emit("\\item " .. esc(b)) end
  emit("\\end{itemize}")
end

local render = {}

function render.education(d)
  local list = visible(d.education)
  if #list == 0 then return false end
  emit("\\resumesection{Education}")
  for _, e in ipairs(list) do
    local head = "\\textbf{" .. esc(e.degree) .. "}"
    if not blank(e.gpa) then head = head .. ", GPA " .. esc(e.gpa) end
    emit(head .. "\\hfill " .. esc(e.gradDate) .. "\\par")
    if not blank(e.school) then emit(esc(e.school) .. "\\par") end
    local cw, ac = joinesc(e.coursework), joinesc(e.activities)
    if cw ~= "" then emit("\\textbf{Relevant coursework:} " .. cw .. "\\par") end
    if ac ~= "" then emit("\\textbf{Activities:} " .. ac .. "\\par") end
    emit("\\vspace{\\itemgap}")
  end
end

function render.projects(d)
  local list = visible(d.projects)
  if #list == 0 then return false end
  emit("\\resumesection{Projects}")
  for _, p in ipairs(list) do
    local tools = joinesc(p.tools)
    local head = "\\textbf{" .. esc(p.title) .. "}"
    if tools ~= "" then head = head .. " (" .. tools .. ")" end
    emit(head .. "\\hfill " .. dates(p.start, p["end"]) .. "\\par")
    bullets(p.bullets)
    emit("\\vspace{\\itemgap}")
  end
end

function render.experience(d)
  local list = visible(d.experience)
  if #list == 0 then return false end
  emit("\\resumesection{Experience}")
  for _, x in ipairs(list) do
    local name = esc(x.title)
    if not blank(x.company) then name = name .. ", " .. esc(x.company) end
    local loc = blank(x.location) and "" or (", " .. esc(x.location))
    if x.engineering then
      emit("\\textbf{" .. name .. "}" .. loc .. "\\hfill " .. dates(x.start, x["end"]) .. "\\par")
      bullets(x.bullets)
    else
      emit(name .. loc .. "\\hfill " .. dates(x.start, x["end"]) .. "\\par")
    end
    emit("\\vspace{\\itemgap}")
  end
end

function render.skills(d)
  local sk = d.skills or {}
  local groups = { { "Software", sk.software }, { "Hardware/Lab", sk.hardwareLab }, { "Certifications", sk.certifications } }
  local lines = {}
  for _, g in ipairs(groups) do
    local v = joinesc(g[2])
    if v ~= "" then lines[#lines + 1] = "\\textbf{" .. g[1] .. ":} " .. v .. "\\par" end
  end
  if #lines == 0 then return false end
  emit("\\resumesection{Skills}")
  for _, l in ipairs(lines) do emit(l) end
end

local function header(h)
  h = h or {}
  emit("\\begin{center}")
  emit(string.format("{\\fontsize{%.1fpt}{%.1fpt}\\selectfont\\textbf{%s}}\\par\\vspace{2pt}", M.font * 1.9, M.font * 2.2, esc(h.name)))
  local c = {}
  if not blank(h.phone) then c[#c + 1] = "\\href{tel:" .. url((h.phone:gsub("[^%d+]", ""))) .. "}{" .. esc(h.phone) .. "}" end
  if not blank(h.email) then c[#c + 1] = "\\href{mailto:" .. url(h.email) .. "}{" .. esc(h.email) .. "}" end
  for _, k in ipairs({ "linkedin", "github" }) do
    if not blank(h[k]) then
      local d = display(h[k])
      c[#c + 1] = "\\href{https://" .. url(d) .. "}{" .. esc(d) .. "}"
    end
  end
  if #c > 0 then emit(table.concat(c, " \\textbar{} ") .. "\\par") end
  local l = {}
  if not blank(h.location) then l[#l + 1] = esc(h.location) end
  if not blank(h.workStatus) then l[#l + 1] = esc(h.workStatus) end
  if h.relocate then l[#l + 1] = "Willing to relocate" end
  if not blank(h.clearance) then l[#l + 1] = esc(h.clearance) end
  if #l > 0 then emit(table.concat(l, " \\textbar{} ") .. "\\par") end
  emit("\\end{center}")
end

function M.body()
  local fh = assert(io.open("resume.json", "r"), "cannot open resume.json")
  local data = decode(fh:read("a")); fh:close()
  header(data.header)
  local order = (data.settings or {}).sectionOrder or { "education", "projects", "experience", "skills" }
  for _, name in ipairs(order) do
    if render[name] then render[name](data) else texio.write_nl("Unknown section in sectionOrder: " .. name) end
  end
  local lines = {}
  for _, chunk in ipairs(out) do for line in (chunk .. "\n"):gmatch("(.-)\n") do lines[#lines + 1] = line end end
  tex.print(lines)
end

return M
