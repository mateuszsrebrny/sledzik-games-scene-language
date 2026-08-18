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

-- Roblox's 3D Importer corrupts a marker node's imported CFrame (both
-- position and rotation), even with a marker mesh-size fix applied. Real
-- baked mesh geometry imports reliably, so a Placement marker is never
-- trusted as-is: `resolveSourceCFrame(assetName, clone)` must derive the
-- source-space placement CFrame for every asset `resolveAsset` can return -
-- from a real anchor part plus a known fixed offset, or (if the marker
-- happens to be authored at identity) that fixed value directly. An asset
-- with no working override fails materialization loudly instead of quietly
-- trusting an import that's known to be unreliable.
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
			error("Runtime asset " .. tostring(assetName) .. " is required by " .. placement.Name
				.. " but is missing from ReplicatedStorage/SGSLAssets - import it, or register it in "
				.. "the server's asset validation so a missing import fails at startup instead of here", 2)
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
				clone:Destroy()
				error("Runtime asset " .. tostring(assetName) .. " has no resolveSourceCFrame override - "
					.. "its imported Placement marker can't be trusted, so a source-space transform must "
					.. "be supplied for it (see MarkerOffsets.lua and scripts/generate_marker_offsets.py)", 2)
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
