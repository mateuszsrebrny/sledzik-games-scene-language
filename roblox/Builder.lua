local Builder = {}

-- Large generated scenes can contain thousands of primitive creations. Yield
-- periodically so Roblox does not terminate the caller for exceeding the
-- synchronous script execution budget.
local primitiveCount = 0

local function yieldAfterBatch()
	primitiveCount += 1
	if primitiveCount % 128 == 0 then
		task.wait()
	end
end

local function rotationCFrame(rotation)
	rotation = rotation or Vector3.zero
	return CFrame.Angles(math.rad(rotation.X), math.rad(rotation.Y), math.rad(rotation.Z))
end

local function applyCommon(part, parent, name, color, material)
	part.Name = name
	part.Anchored = true
	part.Color = color
	part.Material = material or Enum.Material.SmoothPlastic
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.Parent = parent
	yieldAfterBatch()
	return part
end

function Builder.makeCylinder(parent, name, radius, height, position, color, material, rotation)
	local part = Instance.new("Part")
	part.Shape = Enum.PartType.Cylinder
	part.Size = Vector3.new(height, radius * 2, radius * 2)
	part.CFrame = CFrame.new(position) * rotationCFrame(rotation) * CFrame.Angles(0, 0, math.rad(90))

	return applyCommon(part, parent, name, color, material)
end

function Builder.makeBlock(parent, name, size, position, color, material, rotation)
	local part = Instance.new("Part")
	part.Size = size
	part.CFrame = CFrame.new(position) * rotationCFrame(rotation)

	return applyCommon(part, parent, name, color, material)
end

function Builder.makeWedge(parent, name, size, position, color, material, rotation)
	local part = Instance.new("WedgePart")
	part.Size = size
	part.CFrame = CFrame.new(position) * rotationCFrame(rotation)

	return applyCommon(part, parent, name, color, material)
end

function Builder.makeMarker(parent, name, position, rotation)
	local marker = Instance.new("Folder")
	marker.Name = name
	marker:SetAttribute("MarkerPosition", position)
	marker:SetAttribute("MarkerRotation", rotation or Vector3.zero)
	marker.Parent = parent
	return marker
end

function Builder.makeRuntimeAssetMarker(parent, name, assetName, position, rotation, scale, bounds, assetSymbol, robloxId)
	local marker = Builder.makeMarker(parent, name, position, rotation)
	marker:SetAttribute("RuntimeAsset", assetName)
	marker:SetAttribute("RuntimeAssetScale", scale or 1)
	if bounds then
		marker:SetAttribute("RuntimeAssetBounds", bounds)
	end
	if assetSymbol then
		marker:SetAttribute("RuntimeAssetSymbol", assetSymbol)
		marker:SetAttribute("RuntimeAssetWorldPivot", true)
	end
	if robloxId then
		marker:SetAttribute("RuntimeAssetRobloxId", robloxId)
	end
	return marker
end

function Builder.makeSteppedFrustum(parent, name, bottomRadius, topRadius, height, position, color, sliceCount, material, rotation)
	sliceCount = math.max(tonumber(sliceCount) or 4, 1)
	material = material or Enum.Material.SmoothPlastic
	rotation = rotation or Vector3.zero

	local model = Instance.new("Model")
	model.Name = name
	model.Parent = parent

	local sliceHeight = height / sliceCount
	local currentY = -(height / 2)
	local rotationOnly = rotationCFrame(rotation)

	for i = 1, sliceCount do
		local t = (sliceCount == 1) and 1 or ((i - 1) / (sliceCount - 1))
		local radius = math.max(bottomRadius + ((topRadius - bottomRadius) * t), 0.02)
		local centerY = currentY + (sliceHeight / 2)
		local sliceOffset = rotationOnly:VectorToWorldSpace(Vector3.new(0, centerY, 0))

		Builder.makeCylinder(
			model,
			name .. "Slice" .. i,
			radius,
			sliceHeight,
			position + sliceOffset,
			color,
			material,
			rotation
		)

		currentY = currentY + sliceHeight
	end

	return model
end

return Builder
