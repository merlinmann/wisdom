function RawBlock(el)
  if el.format == 'html' then
    -- Remove HTML comments
    el.text = el.text:gsub("<!%-%-.-%-%->" , "")
    -- Clean up extra whitespace
    el.text = el.text:gsub("^%s*$", "")
  end
  -- Return nil to remove empty blocks
  if el.text == "" then
    return {}
  end
  return el
end

function RawInline(el)
  if el.format == 'html' then
    el.text = el.text:gsub("<!%-%-.-%-%->" , "")
    if el.text == "" then
      return {}
    end
  end
  return el
end
