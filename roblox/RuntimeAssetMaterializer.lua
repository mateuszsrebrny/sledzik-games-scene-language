local ImportedAssetNames = require(game.ReplicatedStorage.SceneLanguageImportedAssetNames)
local AssetRegistry = require(game.ReplicatedStorage.SceneLanguageAssetRegistry)

local RuntimeAssetMaterializer = {}

local function findNestedMarker(instance)
	for _, descendant in ipairs(instance:GetDescendants()) do
		if ImportedAssetNames.matches(descendant.Name, "SGSLMarker") then
			return descendant
		end
	end
	return nil
end

local function markerCFrame(instance)
	if instance:IsA("Attachment") then
		return instance.WorldCFrame
	elseif instance:IsA("BasePart") then
		return instance.CFrame
	elseif instance:IsA("Model") then
		local nestedMarker = findNestedMarker(instance)
		if nestedMarker then
			return markerCFrame(nestedMarker)
		end
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

local function findMarker(root, markerName)
	for _, descendant in ipairs(root:GetDescendants()) do
		if ImportedAssetNames.matches(descendant.Name, markerName) then
			return descendant
		end
	end
	return nil
end

local function findNamedPart(root, name)
	for _, descendant in ipairs(root:GetDescendants()) do
		if descendant:IsA("BasePart") and descendant.Name == name then
			return descendant
		end
	end
	return nil
end
RuntimeAssetMaterializer.findNamedPart = findNamedPart

local function collectPlacementMarkers(root)
	local markers = {}
	for _, descendant in ipairs(root:GetDescendants()) do
		if descendant:GetAttribute("RuntimeAsset") then
			table.insert(markers, descendant)
		end
	end
	table.sort(markers, function(left, right)
		return left.Name < right.Name
	end)
	return markers
end

local function createMissingAssetPlaceholder(placement, assetName, targetCFrame, scale)
	local bounds = placement:GetAttribute("RuntimeAssetBounds")
	if typeof(bounds) ~= "Vector3" then
		bounds = Vector3.new(2, 2, 2)
	end
	local placeholder = Instance.new("Part")
	placeholder.Name = placement.Name
	placeholder.Size = bounds * scale
	placeholder.CFrame = targetCFrame
	placeholder.Anchored = true
	placeholder.CanCollide = false
	placeholder.CanTouch = false
	placeholder.CanQuery = false
	placeholder.Transparency = 0.55
	placeholder.Color = Color3.fromRGB(245, 158, 11)
	placeholder.Material = Enum.Material.Neon
	placeholder:SetAttribute("MissingRuntimeAsset", assetName)
	placeholder.Parent = placement.Parent
	warn("Missing runtime asset " .. tostring(assetName) .. "; using bounds placeholder")
	return placeholder
end

-- Roblox's 3D Importer corrupts a marker node's imported CFrame (both
-- position and rotation), even with a marker mesh-size fix applied. Real
-- baked mesh geometry imports reliably, so a Placement marker cannot always
-- be trusted as-is. `resolveSourceCFrame(assetName, clone)`, if provided, is
-- tried first for each asset and lets the caller derive the source-space
-- placement CFrame from a real anchor part plus a known fixed offset
-- instead; returning nil/false falls back to trusting the clone's own
-- Placement marker.
function RuntimeAssetMaterializer.materialize(root, resolveAsset, resolveSourceCFrame)
	local materialized = {}
	for index, placement in ipairs(collectPlacementMarkers(root)) do
		local assetName = placement:GetAttribute("RuntimeAsset")
		local targetCFrame = markerCFrame(placement)
		local source = resolveAsset(assetName)
		if not targetCFrame then
			error("Runtime asset placement " .. placement.Name .. " has no valid transform", 2)
		end
		local scale = placement:GetAttribute("RuntimeAssetScale") or 1
		if not source or not source:IsA("Model") then
			table.insert(materialized, createMissingAssetPlaceholder(placement, assetName, targetCFrame, scale))
			placement:Destroy()
			continue
		end

		local clone = source:Clone()
		clone.Name = placement.Name
		clone.Parent = placement.Parent
		AssetRegistry.stripVersionMarker(clone)
		if scale ~= 1 then
			clone:ScaleTo(scale)
		end

		if placement:GetAttribute("RuntimeAssetWorldPivot") then
			clone:PivotTo(targetCFrame)
		else
			local sourceCFrame = resolveSourceCFrame and resolveSourceCFrame(assetName, clone) or nil
			if not sourceCFrame then
				local sourcePlacement = findMarker(clone, "Placement")
				sourceCFrame = sourcePlacement and markerCFrame(sourcePlacement)
			end
			if not sourceCFrame then
				clone:Destroy()
				error("Runtime asset " .. assetName .. " is missing a Placement marker", 2)
			end
			clone:PivotTo(targetCFrame * sourceCFrame:Inverse() * clone:GetPivot())
		end
		clone:SetAttribute("RuntimeAsset", assetName)
		clone:SetAttribute("RuntimeAssetPlacement", placement.Name)
		for _, descendant in ipairs(clone:GetDescendants()) do
			if descendant:IsA("BasePart") then
				descendant.Anchored = true
			end
		end
		placement:Destroy()
		table.insert(materialized, clone)

		if index % 16 == 0 then
			task.wait()
		end
	end
	return materialized
end

return RuntimeAssetMaterializer
