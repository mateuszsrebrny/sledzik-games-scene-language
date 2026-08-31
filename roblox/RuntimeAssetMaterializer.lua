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

-- SGSL gives every marker (Placement, Grip, WorkerPoint, ...) a small
-- placeholder mesh so Roblox's importer keeps it as a real descendant
-- instead of discarding an empty node - see glb_renderer.py's
-- _append_marker_mesh. Nothing here ever hid it: this module locates a
-- nested SGSLMarker (findNestedMarker, above) to read its CFrame, but never
-- to hide it, unlike the bucket/bottle/six-pack construction paths that
-- each do their own `isInsideToolMarker`-style check. Every asset placed
-- through `materialize` - Pump, PumpMirrored, GutterSystem, every
-- HouseGarden variant - carries at least one such marker (GutterSystem's
-- own Placement marker is explicitly authored, per V0Game.server.lua's own
-- comment on it), so each left a small visible cube on its clone. Same fix
-- as the six-pack's (de29dfd), generalized to the one place all of these
-- assets actually get built, so no future asset needs its own copy of it.
local function hideMarkerMeshes(clone)
	for _, descendant in ipairs(clone:GetDescendants()) do
		if descendant:IsA("BasePart") and ImportedAssetNames.matches(descendant.Name, "SGSLMarker") then
			descendant.Transparency = 1
			descendant.CanCollide = false
			descendant.CanTouch = false
			descendant.CanQuery = false
		end
	end
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

-- `bounds` on an `asset` declares the box the asset occupies in the scene, and
-- this is where that becomes true rather than merely stated. Model:ScaleTo is a
-- multiplier on the model's *own* size, so a scale computed against a declared
-- size is only right if the declaration happens to match the import - and
-- nothing checked that it did. The preview renderer draws the declared box, so
-- a wrong declaration looked correct in preview and arrived oversized in
-- Roblox, which is exactly how the town fountain grew past the square it stands
-- on.
--
-- So measure the import and fit it inside the box instead. Uniform, because
-- ScaleTo is uniform: the tightest axis wins, and the asset can never exceed
-- what SGSL declared for it.
-- Measured from the BaseParts rather than with Model:GetExtentsSize, for the
-- same reason placeBottleOnSurface stopped using Model:GetBoundingBox: a
-- model's own box counts every part in it, and an imported asset's marker
-- placeholders sit wherever Studio's importer left them - which once inflated a
-- bottle past 100 studs. A part's box is turned into world axes by projecting
-- its half-size through the absolute values of its rotation, so a rotated part
-- contributes the space it really takes up.
local function measureExtents(model)
	local minimum, maximum = nil, nil
	for _, part in ipairs(model:GetDescendants()) do
		if part:IsA("BasePart") then
			local cframe, size = part.CFrame, part.Size
			local right, up, look = cframe.RightVector, cframe.UpVector, cframe.LookVector
			local reach = Vector3.new(
				math.abs(right.X) * size.X + math.abs(up.X) * size.Y + math.abs(look.X) * size.Z,
				math.abs(right.Y) * size.X + math.abs(up.Y) * size.Y + math.abs(look.Y) * size.Z,
				math.abs(right.Z) * size.X + math.abs(up.Z) * size.Y + math.abs(look.Z) * size.Z
			) / 2
			local position = cframe.Position
			minimum = minimum and minimum:Min(position - reach) or (position - reach)
			maximum = maximum and maximum:Max(position + reach) or (position + reach)
		end
	end
	if not minimum then
		return nil
	end
	return maximum - minimum
end
RuntimeAssetMaterializer.measureExtents = measureExtents

-- Uniform, because Model:ScaleTo is uniform: the tightest axis wins, so the
-- asset fills the box on that axis and can never exceed it on any.
local function fitScale(measured, box)
	return math.min(box.X / measured.X, box.Y / measured.Y, box.Z / measured.Z)
end
RuntimeAssetMaterializer.fitScale = fitScale

local function fitToBounds(clone, box, assetName, placementName)
	local measured = measureExtents(clone)
	if not measured or measured.X <= 0 or measured.Y <= 0 or measured.Z <= 0 then
		error("Runtime asset " .. tostring(assetName) .. " placed by " .. placementName
			.. " has no measurable extents to fit into its declared bounds", 2)
	end

	local fit = fitScale(measured, box)
	clone:ScaleTo(fit)
	return measured * fit
end

-- The declared box is centred on the placement, because SGSL already moved
-- `at` from the anchored face to the centre when it generated the marker. A
-- uniform fit leaves the model short of the box on at least two axes, so an
-- anchored face has to be re-seated against what the model actually measures -
-- otherwise `anchor bottom` leaves a fitted model hovering above the ground by
-- half the slack.
local function anchorOffset(anchor, box, measured)
	local slack = (box - measured) / 2
	local names = {}
	for value in string.gmatch(tostring(anchor or ""), "[^,]+") do
		table.insert(names, value)
	end

	local x = (names[1] == "left" and -slack.X) or (names[1] == "right" and slack.X) or 0
	local y = (names[2] == "bottom" and -slack.Y) or (names[2] == "top" and slack.Y) or 0
	local z = (names[3] == "front" and -slack.Z) or (names[3] == "back" and slack.Z) or 0
	return Vector3.new(x, y, z)
end
RuntimeAssetMaterializer.anchorOffset = anchorOffset

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
		hideMarkerMeshes(clone)

		local bounds = placement:GetAttribute("RuntimeAssetBounds")
		local anchor = placement:GetAttribute("RuntimeAssetAnchor")
		local fitted = nil
		if typeof(bounds) == "Vector3" then
			fitted = fitToBounds(clone, bounds * scale, assetName, placement.Name)
		elseif scale ~= 1 then
			clone:ScaleTo(scale)
		end

		if placement:GetAttribute("RuntimeAssetWorldPivot") then
			clone:PivotTo(targetCFrame)
			if fitted then
				-- targetCFrame is the centre of the declared box, so the model's
				-- own pivot now sits there too. Slide it along the box's axes
				-- until the anchored faces meet.
				clone:PivotTo(clone:GetPivot() * CFrame.new(anchorOffset(anchor, bounds * scale, fitted)))
			end
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
