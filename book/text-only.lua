-- Keep the readable text, captions, emphasis, and links; omit every image.
function Image() return {} end
function Figure(figure) return figure.caption.long end
function Link(link)
  if pandoc.utils.stringify(link.content) == "" then return {} end
end
