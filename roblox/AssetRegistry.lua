local ReplicatedStorage = game:GetService("ReplicatedStorage")

local ImportedAssetNames = require(game.ReplicatedStorage.SceneLanguageImportedAssetNames)

local AssetRegistry = {}
local warnedMissing = {}

local function findDescendant(instance, name)
	for _, descendant in ipairs(instance:GetDescendants()) do
		if descendant.Name == name then
			return descendant
		end
	end
	-- SGSL exports segmented primitives with names such as
	-- CollectionFunnel_segment_01 and WaterBottom_segment_01_segment_01.
	-- Treat the base semantic name as present when one of those segments exists.
	for _, descendant in ipairs(instance:GetDescendants()) do
		local nameStart = string.find(descendant.Name, name, 1, true)
		while nameStart do
			local nameEnd = nameStart + #name - 1
			local before = nameStart > 1 and descendant.Name:sub(nameStart - 1, nameStart - 1) or nil
			local after = nameEnd < #descendant.Name and descendant.Name:sub(nameEnd + 1, nameEnd + 1) or nil
			local validBefore = before == nil or before == "." or before == "_"
			local validAfter = after == nil or after == "." or after == "_"
			if validBefore and validAfter then
				return descendant
			end
			nameStart = string.find(descendant.Name, name, nameStart + 1, true)
		end
	end
	return nil
end

local function findBasePart(instance, name)
	if not instance then
		return nil
	end
	local descendant = findDescendant(instance, name)
	if not descendant then
		return nil
	end
	if descendant:IsA("BasePart") then
		return descendant
	end
	return descendant:FindFirstChildWhichIsA("BasePart", true)
end

local function findSemanticDescendant(instance, name)
	for _, descendant in ipairs(instance:GetDescendants()) do
		if string.lower(descendant.Name) == string.lower(name) then
			return descendant
		end
	end
	return nil
end

local function hasNestedSGSLMarker(instance)
	for _, descendant in ipairs(instance:GetDescendants()) do
		if string.lower(descendant.Name) == "sgslmarker" then
			return descendant:IsA("BasePart") or descendant:IsA("Attachment")
		end
	end
	return false
end

local function markerTransform(instance)
	if instance:IsA("Attachment") then
		return instance.WorldCFrame
	elseif instance:IsA("BasePart") then
		return instance.CFrame
	elseif instance:IsA("Model") then
		local nestedMarker = findSemanticDescendant(instance, "SGSLMarker")
		if nestedMarker then
			return markerTransform(nestedMarker)
		end
		return instance:GetPivot()
	end
	local position = instance:GetAttribute("MarkerPosition")
	local rotation = instance:GetAttribute("MarkerRotation")
	if typeof(position) ~= "Vector3" then
		return nil
	end
	return CFrame.new(position) * (typeof(rotation) == "Vector3"
		and CFrame.Angles(math.rad(rotation.X), math.rad(rotation.Y), math.rad(rotation.Z))
		or CFrame.new())
end

local function isFiniteNumber(value)
	return value == value and math.abs(value) < math.huge
end

local function isFiniteVector3(value)
	return typeof(value) == "Vector3"
		and isFiniteNumber(value.X)
		and isFiniteNumber(value.Y)
		and isFiniteNumber(value.Z)
end

local function addTransformError(errors, instance, label)
	local transform = markerTransform(instance)
	if not transform or not isFiniteVector3(transform.Position) then
		table.insert(errors, label .. " has an invalid transform")
	end
end

-- Reads the content-version hash embedded by glb_renderer.py as an
-- "SGSLVersion_<hash>" node. Returns nil if the imported prefab predates
-- version checking (never reimported since this feature shipped).
local function findAssetVersion(instance)
	for _, descendant in ipairs(instance:GetDescendants()) do
		local hash = ImportedAssetNames.extractVersionHash(descendant.Name)
		if hash then
			return hash
		end
	end
	return nil
end

local function resolveAsset(assets, name)
	local asset = assets:FindFirstChild(name)
	if asset then
		return asset
	end

	return nil
end

-- Every gameplay clone of a compiled prefab carries a leftover
-- SGSLVersion_<hash> marker node (validateAssets only needs it on the
-- source model in ReplicatedStorage/SGSLAssets). That node is a real
-- BasePart with whatever CFrame Roblox's importer gave it, which can land
-- far from the rest of the model when the same node-transform precision
-- issue that still affects Grip's rotation also displaces it - inflating
-- GetBoundingBox() on the clone and throwing off any bottom/surface
-- alignment math. Call this right after cloning a compiled prefab, before
-- any geometry normalization runs.
function AssetRegistry.stripVersionMarker(instance)
	for _, descendant in ipairs(instance:GetDescendants()) do
		if ImportedAssetNames.extractVersionHash(descendant.Name) then
			descendant:Destroy()
		end
	end
end

-- Looks up a compiled SGSL prefab by name under ReplicatedStorage/SGSLAssets.
-- Warns once per distinct name if it's missing, then keeps returning nil
-- silently so callers don't need their own per-name warned-state.
function AssetRegistry.getAsset(name)
	local assets = ReplicatedStorage:FindFirstChild("SGSLAssets")
	local asset = assets and resolveAsset(assets, name)
	if asset then
		return asset
	end

	if not warnedMissing[name] then
		warn("Required compiled SGSL asset is unavailable at ReplicatedStorage/SGSLAssets/" .. name)
		warnedMissing[name] = true
	end
	return nil
end

function AssetRegistry.findBasePart(instance, name)
	return findBasePart(instance, name)
end

function AssetRegistry.validateAssets(specs)
	local errors = {}
	local assets = ReplicatedStorage:FindFirstChild("SGSLAssets")
	if not assets then
		return { "Missing ReplicatedStorage/SGSLAssets folder" }
	end

	for _, spec in ipairs(specs) do
		local asset = resolveAsset(assets, spec.name)
		if not asset then
			table.insert(errors, "Missing ReplicatedStorage/SGSLAssets/" .. spec.name)
		else
			if not asset:IsA("Model") then
				table.insert(errors, spec.name .. " must be a Model, got " .. asset.ClassName)
			end
			if spec.version then
				local foundVersion = findAssetVersion(asset)
				if not foundVersion then
					table.insert(errors, spec.name .. " has no SGSLVersion marker - it was imported before "
						.. "version checking existed. Reimport " .. spec.name
						.. " (see docs/roblox-imported-assets.md).")
				elseif foundVersion ~= spec.version then
					table.insert(errors, spec.name .. " in Studio is out of date (has version " .. foundVersion
						.. ", the current .sgsl source expects " .. spec.version .. "). Regenerate and reimport "
						.. spec.name .. ".glb (see docs/roblox-imported-assets.md).")
				end
			end
			for _, descendantName in ipairs(spec.descendants or {}) do
				local descendant = findDescendant(asset, descendantName)
				if not findBasePart(asset, descendantName) then
					table.insert(errors, spec.name .. " is missing BasePart descendant " .. descendantName)
				elseif descendant then
					addTransformError(errors, descendant, spec.name .. "." .. descendantName)
				end
			end
			for _, markerName in ipairs(spec.markers or {}) do
				local marker = findDescendant(asset, markerName)
				if not marker then
					table.insert(errors, spec.name .. " is missing marker descendant " .. markerName)
				else
					addTransformError(errors, marker, spec.name .. "." .. markerName)
				end
			end
			for _, markerName in ipairs(spec.nestedMarkers or {}) do
				local marker = findSemanticDescendant(asset, markerName)
				if not marker then
					table.insert(errors, spec.name .. " is missing marker container " .. markerName)
				elseif not hasNestedSGSLMarker(marker) then
					table.insert(errors, spec.name .. "." .. markerName .. " must contain SGSLMarker")
				else
					local nestedMarker = findSemanticDescendant(marker, "SGSLMarker")
					addTransformError(errors, nestedMarker, spec.name .. "." .. markerName .. ".SGSLMarker")
				end
			end
		end
	end

	return errors
end

return AssetRegistry
