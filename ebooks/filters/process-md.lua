


function HorizontalRule(el)
  return pandoc.RawBlock('html', '<div style="page-break-before: always;"></div>')
end

function BulletList(el)
  local result = {}
  for i, item in ipairs(el.content) do
    if i > 1 then
      table.insert(result, pandoc.RawBlock('html', '<div style="page-break-before: always;"></div>'))
    end

    -- Wrap item content in div with center-page class
    local div = pandoc.Div(item, {class = "center-page"})
    table.insert(result, pandoc.BulletList({div}))
  end
  return result
end

function OrderedList(el)
  local result = {}
  for i, item in ipairs(el.content) do
    if i > 1 then
      table.insert(result, pandoc.RawBlock('html', '<div style="page-break-before: always;"></div>'))
    end

    -- Wrap item content in div with center-page class
    local div = pandoc.Div(item, {class = "center-page"})
    table.insert(result, pandoc.OrderedList({div}))
  end
  return result
end
