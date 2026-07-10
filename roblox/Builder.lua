local Builder = {}

local function applyCommon(part, parent, name, color, material)
	part.Name = name
	part.Anchored = true
	part.Color = color
	part.Material = material or Enum.Material.SmoothPlastic
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.Parent = parent
	return part
end

function Builder.makeCylinder(parent, name, radius, height, position, color, material)
	local part = Instance.new("Part")
	part.Shape = Enum.PartType.Cylinder
	part.Size = Vector3.new(height, radius * 2, radius * 2)
	part.CFrame = CFrame.new(position) * CFrame.Angles(0, 0, math.rad(90))

	return applyCommon(part, parent, name, color, material)
end

function Builder.makeBlock(parent, name, size, position, color, material)
	local part = Instance.new("Part")
	part.Size = size
	part.Position = position

	return applyCommon(part, parent, name, color, material)
end

function Builder.makeSteppedFrustum(parent, name, bottomRadius, topRadius, height, position, color, sliceCount, material)
	sliceCount = math.max(tonumber(sliceCount) or 4, 1)
	material = material or Enum.Material.SmoothPlastic

	local model = Instance.new("Model")
	model.Name = name
	model.Parent = parent

	local sliceHeight = height / sliceCount
	local currentY = position.Y - (height / 2)

	for i = 1, sliceCount do
		local t = (sliceCount == 1) and 1 or ((i - 1) / (sliceCount - 1))
		local radius = bottomRadius + ((topRadius - bottomRadius) * t)
		local centerY = currentY + (sliceHeight / 2)

		Builder.makeCylinder(
			model,
			name .. "Slice" .. i,
			radius,
			sliceHeight,
			Vector3.new(position.X, centerY, position.Z),
			color,
			material
		)

		currentY = currentY + sliceHeight
	end

	return model
end

return Builder
