-- Enable this to _replace_ horizontal rules with a page break
-- Currently, style.css applies this class to all <hr> elements
-- function HorizontalRule(el)
--   return pandoc.RawBlock('html', '<div class="page-break"></div>')
-- end

function center_and_page_separate(el)
  -- Convert to raw HTML to add classes to <li> elements
  local items = {}
  for i, item in ipairs(el.content) do
    local item_html = pandoc.write(pandoc.Pandoc(item), 'html')
    -- Remove any existing <p> tags if they wrap the content
    item_html = item_html:gsub('<p>(.-)</p>', '%1')
    table.insert(items, '<li class="center-page page-break">' .. item_html .. '</li>')
  end

  return pandoc.RawBlock('html', '<ul>' .. table.concat(items, '\n') .. '</ul>')
end

-- Apply the same transformation to BulletList and OrderedList
BulletList = center_and_page_separate
OrderedList = center_and_page_separate
