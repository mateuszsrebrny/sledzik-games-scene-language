local ImportedAssetNames = {}

function ImportedAssetNames.normalize(name)
	return tostring(name):lower():gsub("[._]node$", "")
end

function ImportedAssetNames.matches(name, semanticName)
	return ImportedAssetNames.normalize(name) == string.lower(semanticName)
end

-- Content-version markers are exported as "SGSLVersion_<hash>" nodes (see
-- glb_renderer.py). Returns the hash portion, or nil if `name` isn't one.
function ImportedAssetNames.extractVersionHash(name)
	return ImportedAssetNames.normalize(name):match("^sgslversion_(%w+)$")
end

return ImportedAssetNames
