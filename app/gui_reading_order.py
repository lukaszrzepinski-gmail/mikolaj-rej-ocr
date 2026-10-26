"""Column-aware reading order using Kraken's geometric partial-order rules.

No ML imports: existing cached previews can be reordered without segmentation.
No coordinates or lines are removed/changed.
"""
POLICY = 'columns-layout-v2'


def order_lines(lines, layout='auto'):
    if layout not in ('auto','single','two'):
        raise ValueError('Nieznany uklad kolumn')
    if len(lines) < 2:
        return list(lines)
    bounds = []
    for index,line in enumerate(lines):
        points = line.get('baseline') or line.get('boundary')
        if not points:
            return list(lines)  # Preserve explicit incomplete/user geometry.
        xs,ys = zip(*points)
        bounds.append((min(ys),max(ys),min(xs),max(xs)))
    by_height=lambda index:((bounds[index][0]+bounds[index][1])/2,bounds[index][2])
    if layout == 'single':
        return [lines[index] for index in sorted(range(len(lines)),key=by_height)]
    if layout == 'two':
        middle=(min(bound[2] for bound in bounds)+max(bound[3] for bound in bounds))/2
        spanning=sorted((i for i,b in enumerate(bounds) if b[2]<middle<b[3]),key=by_height)
        remaining=set(range(len(lines)))-set(spanning)
        result=[]
        def columns(indices):
            left=[i for i in indices if (bounds[i][2]+bounds[i][3])/2<=middle]
            right=[i for i in indices if i not in left]
            return sorted(left,key=by_height)+sorted(right,key=by_height)
        for wide in spanning:
            above={i for i in remaining if by_height(i)[0]<by_height(wide)[0]}
            result.extend(columns(above));result.append(wide);remaining-=above
        result.extend(columns(remaining))
        return [lines[index] for index in result]
    count = len(bounds)
    predecessors = [[] for _ in bounds]
    for i,u in enumerate(bounds):
        for j,v in enumerate(bounds):
            if u[2] < v[3] and u[3] > v[2]:
                before = u[0] < v[0]
            elif u[3] < v[2]:
                separated = any(w != u and w != v and
                    w[1] >= min(u[0],v[0]) and w[0] <= max(u[1],v[1]) and
                    w[2] < u[3] and w[3] > v[2] for w in bounds)
                before = not separated
            else:
                before = False
            if before:
                predecessors[j].append(i)
    # Iterative form of Kraken topsort; stable and safe for long pages.
    visited = set(); result = []
    for index in range(count):
        stack = [(index,False)]
        while stack:
            node,expanded = stack.pop()
            if expanded:
                result.append(node)
            elif node not in visited:
                visited.add(node)
                stack.append((node,True))
                stack.extend((parent,False) for parent in reversed(predecessors[node]))
    assert len(result)==count and len(set(result))==count
    return [lines[index] for index in result]


def redraw_preview(image, rotation, lines, destination):
    from PIL import Image,ImageDraw,ImageFont
    with Image.open(image) as original:
        canvas = original.convert('RGB')
    if rotation:
        canvas = canvas.rotate(-rotation,expand=True)
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    except OSError:
        font = ImageFont.load_default()
    for number,line in enumerate(lines,1):
        points = [tuple(point) for point in line['baseline']]
        if len(points)>=2:
            draw.line(points,fill=(220,20,20),width=3)
            draw.text((points[0][0]+3,points[0][1]-20),str(number),fill=(20,20,220),font=font)
    if canvas.width>1100:
        canvas = canvas.resize((1100,int(canvas.height*1100/canvas.width)))
    canvas.save(destination,'PNG',compress_level=1)
