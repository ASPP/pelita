
CanvasRenderingContext2D::roundRect = (x, y, w, h, r) ->
  r = w / 2 if (w < 2 * r)
  r = h / 2 if (h < 2 * r)
  this.beginPath()
  this.moveTo(x+r, y)
  this.arcTo(x+w, y,   x+w, y+h, r)
  this.arcTo(x+w, y+h, x,   y+h, r)
  this.arcTo(x,   y+h, x,   y,   r)
  this.arcTo(x,   y,   x+w, y,   r)
  this.closePath()
  this


this.Maze = class Maze

  constructor: (@canvas, @width, @height, @maze, @food, @bot_positions) ->
    #@width ?= @canvas.data("maze-width")
    #@height ?= @canvas.data("maze-height")
    #@maze ?= @canvas.data("maze-walls")
    #@bot_positions ?= @canvas.data("maze-bot-positions")

    @canvas.data("maze-width", @width)
    @canvas.data("maze-height", @height)
    @canvas.data("maze-walls", @maze)
    @canvas.data("maze-food", @maze)
    @canvas.data("maze-bot-positions", @bot_positions)

    @ctx = @canvas[0].getContext "2d"

    @defaultScale = 12

    @scale = @canvas[0].height / @height

    @ctx.fillStyle = '#FFEECC'
    @ctx.fillRect(0, 0, @width * @scale, @height * @scale)

    @ctx.strokeStyle = '#fa00ff'
    @ctx.lineWidth = 5
    @ctx.lineCap = 'round'

    @ctx.fillStyle = "#44BBDD" # "rgba(0, 0, 255, .5)"

  scaleX: (x) ->
    @scale + @scale * x

  scaleY: (y) ->
    @scale + @scale * y

  get_wall: (i, j) ->
    return false if i < 0 or j < 0 or i >= @width or j >= @height
    "#" in @maze[j * @width + i]

  line_to: (x, y, x2, y2) ->
    #@ctx.roundRect(x1, y1, x2, y2, 1)
    w = x2 - x
    h = y2 - y
    r = 2
    r = w / 2 if (w < 2 * r)
    r = h / 2 if (h < 2 * r)
    @ctx.beginPath()
    @ctx.moveTo(x+r, y)
    @ctx.arcTo(x+w, y,   x+w, y+h, r)
    @ctx.arcTo(x+w, y+h, x,   y+h, r)
    @ctx.arcTo(x,   y+h, x,   y,   r)
    @ctx.arcTo(x,   y,   x+w, y,   r)
    @ctx.closePath()
    @ctx

  draw_food: (i, j) ->
    @ctx.save()
    @ctx.lineWidth = @scale / 12
    @ctx.fillStyle = '#ee8811' #'#FF7766'
    @ctx.strokeStyle = '#ee8811' # '#FF7766'
    @ctx.beginPath()
    @ctx.arc((i + 0.5) * @scale, (j + 0.5) * @scale, @scale / 4.0, 0 , 2 * Math.PI, false)
    @ctx.fill()
    #@ctx.stroke()
    @ctx.closePath()
    @ctx.restore()
    @ctx

  draw_bot: (idx, i, j) ->
    @ctx.save()
    @ctx.lineWidth = @scale / 6
    @ctx.fillStyle = '#FFEECC' #'#FF7766'
    if idx % 2 == 0
      @ctx.strokeStyle = '#44BBDD'
    else
      @ctx.strokeStyle = '#FF7766'
    # @ctx.strokeStyle = '#FF7766'
    @ctx.beginPath()
    @ctx.arc((i + 0.5) * @scale, (j + 0.5) * @scale, @scale / 3.0, 0 , 2 * Math.PI, false)
    @ctx.fill()
    @ctx.stroke()
    @ctx.closePath()
    @ctx.restore()
    @ctx

  draw: ->
    if @bot_positions
      for bot, idx in @bot_positions
        @draw_bot(idx, bot...)
    for i in [0 ... @width]
      if i < @width / 2
        @ctx.fillStyle = '#44BBDD'
      else
        @ctx.fillStyle = '#FF7766'
      for j in [0 ... @height]
        if @get_wall(i, j)
          #@ctx.roundRect(i * @scale, j * @scale, @scale, @scale, 2)
          #@ctx.fill()
          @ctx.fillRect(i * @scale, j * @scale, @scale, @scale)
    for [i, j] in @food
      @draw_food(i, j)
    return

this.createMaze = (args...) ->
  new Maze(args...).draw()
