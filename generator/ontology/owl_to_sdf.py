import sys
import argparse
import signal
from rdflib import Graph, Namespace, RDF, URIRef, Literal
import xml.etree.ElementTree as ET
import xml.dom.minidom
import difflib
from pathlib import Path
import re

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

SDF = Namespace("http://season.ai4sim/sdf#")

def _pretty_xml(xml_text):
    try:
        d = xml.dom.minidom.parseString(xml_text)
        return d.toprettyxml(indent="  ")
    except Exception:
        return xml_text

def _normalize_xml(xml_text):
    return "\n".join([l.rstrip() for l in _pretty_xml(xml_text).splitlines() if l.strip() != ""])

def _normalize_fragment(xml_text: str) -> str:
    norm = _normalize_xml(xml_text)
    norm = "\n".join([l for l in norm.splitlines() if not l.strip().startswith("<?xml")])
    return norm.strip()

def _write_el_text(el, text):
    if el.text and el.text.strip():
        el.text += text
    else:
        el.text = text

def build_collision_element(g: Graph, node: URIRef):
    el = ET.Element("collision")
    for val in g.objects(node, SDF.collisionName):
        el.set("name", str(val))
    for pose in g.objects(node, SDF.hasPose):
        p_el = ET.SubElement(el, "pose")
        for v in g.objects(pose, SDF.poseValue):
            _write_el_text(p_el, str(v))
    for geom in g.objects(node, SDF.hasGeometry):
        ge_el = ET.SubElement(el, "geometry")
        for box in g.objects(geom, SDF.hasBox):
            b_el = ET.SubElement(ge_el, "box")
            for size in g.objects(box, SDF.hasSize):
                s_el = ET.SubElement(b_el, "size")
                for v in g.objects(size, SDF.sizeValue):
                    _write_el_text(s_el, str(v))
    for surf in g.objects(node, SDF.hasSurface):
        s_el = ET.SubElement(el, "surface")
        for contact in g.objects(surf, SDF.hasContact):
            c_el = ET.SubElement(s_el, "contact")
            for ode in g.objects(contact, SDF.hasOde):
                o_el = ET.SubElement(c_el, "ode")
                for v in g.objects(ode, SDF.minDepthValue):
                    md = ET.SubElement(o_el, "min_depth")
                    _write_el_text(md, str(v))
                for v in g.objects(ode, SDF.maxVelValue):
                    mv = ET.SubElement(o_el, "max_vel")
                    _write_el_text(mv, str(v))
        for friction in g.objects(surf, SDF.hasFriction):
            f_el = ET.SubElement(s_el, "friction")
            for ode in g.objects(friction, SDF.hasOde):
                ET.SubElement(f_el, "ode")
    return el

def build_inertial_element(g: Graph, node: URIRef):
    el = ET.Element("inertial")
    for mass in g.objects(node, SDF.Mass):
        for v in g.objects(mass, SDF.massValue):
            m_el = ET.SubElement(el, "mass")
            _write_el_text(m_el, str(v))
    for inertia in g.objects(node, SDF.Inertia):
        in_el = ET.SubElement(el, "inertia")
        def _sub(tag, cls, prop):
            for obj in g.objects(inertia, cls):
                for v in g.objects(obj, prop):
                    t = ET.SubElement(in_el, tag)
                    _write_el_text(t, str(v))
        _sub("ixx", SDF.Ixx, SDF.ixxValue)
        _sub("ixy", SDF.Ixy, SDF.ixyValue)
        _sub("ixz", SDF.Ixz, SDF.ixzValue)
        _sub("iyy", SDF.Iyy, SDF.iyyValue)
        _sub("iyz", SDF.Iyz, SDF.iyzValue)
        _sub("izz", SDF.Izz, SDF.izzValue)
    return el

def graph_from_inline_sample(kind: str) -> tuple[Graph, URIRef]:
    g = Graph()
    if kind == "collision":
        col = URIRef("http://season.ai4sim/inst#col1")
        p = URIRef("http://season.ai4sim/inst#p1")
        geom = URIRef("http://season.ai4sim/inst#g1")
        box = URIRef("http://season.ai4sim/inst#b1")
        size = URIRef("http://season.ai4sim/inst#sz1")
        surf = URIRef("http://season.ai4sim/inst#s1")
        contact = URIRef("http://season.ai4sim/inst#c1")
        ode1 = URIRef("http://season.ai4sim/inst#o1")
        friction = URIRef("http://season.ai4sim/inst#f1")
        ode2 = URIRef("http://season.ai4sim/inst#o2")
        g.add((col, RDF.type, SDF.Collision))
        g.add((col, SDF.collisionName, Literal("sample_collision")))
        g.add((col, SDF.hasPose, p))
        g.add((p, RDF.type, SDF.Pose))
        g.add((p, SDF.poseValue, Literal("0 0 0 0 0 0")))
        g.add((col, SDF.hasGeometry, geom))
        g.add((geom, RDF.type, SDF.Geometry))
        g.add((geom, SDF.hasBox, box))
        g.add((box, RDF.type, SDF.Box))
        g.add((box, SDF.hasSize, size))
        g.add((size, RDF.type, SDF.Size))
        g.add((size, SDF.sizeValue, Literal("1 1 1")))
        g.add((col, SDF.hasSurface, surf))
        g.add((surf, RDF.type, SDF.Surface))
        g.add((surf, SDF.hasContact, contact))
        g.add((contact, RDF.type, SDF.Contact))
        g.add((contact, SDF.hasOde, ode1))
        g.add((ode1, RDF.type, SDF.ODE))
        g.add((ode1, SDF.minDepthValue, Literal("0.001")))
        g.add((ode1, SDF.maxVelValue, Literal("0")))
        g.add((surf, SDF.hasFriction, friction))
        g.add((friction, RDF.type, SDF.Friction))
        g.add((friction, SDF.hasOde, ode2))
        g.add((ode2, RDF.type, SDF.ODE))
        return g, col
    if kind == "inertial":
        inert = URIRef("http://season.ai4sim/inst#inert1")
        mass = URIRef("http://season.ai4sim/inst#m1")
        inertia = URIRef("http://season.ai4sim/inst#I")
        ixx = URIRef("http://season.ai4sim/inst#ixx")
        ixy = URIRef("http://season.ai4sim/inst#ixy")
        ixz = URIRef("http://season.ai4sim/inst#ixz")
        iyy = URIRef("http://season.ai4sim/inst#iyy")
        iyz = URIRef("http://season.ai4sim/inst#iyz")
        izz = URIRef("http://season.ai4sim/inst#izz")
        g.add((inert, RDF.type, SDF.Inertial))
        g.add((inert, SDF.Mass, mass))
        g.add((mass, RDF.type, SDF.Mass))
        g.add((mass, SDF.massValue, Literal("2.0")))
        g.add((inert, SDF.Inertia, inertia))
        g.add((inertia, RDF.type, SDF.Inertia))
        g.add((inertia, SDF.Ixx, ixx)); g.add((ixx, RDF.type, SDF.Ixx)); g.add((ixx, SDF.ixxValue, Literal("0.02166666666666667")))
        g.add((inertia, SDF.Ixy, ixy)); g.add((ixy, RDF.type, SDF.Ixy)); g.add((ixy, SDF.ixyValue, Literal("0")))
        g.add((inertia, SDF.Ixz, ixz)); g.add((ixz, RDF.type, SDF.Ixz)); g.add((ixz, SDF.ixzValue, Literal("0")))
        g.add((inertia, SDF.Iyy, iyy)); g.add((iyy, RDF.type, SDF.Iyy)); g.add((iyy, SDF.iyyValue, Literal("0.02166666666666667")))
        g.add((inertia, SDF.Iyz, iyz)); g.add((iyz, RDF.type, SDF.Iyz)); g.add((iyz, SDF.iyzValue, Literal("0")))
        g.add((inertia, SDF.Izz, izz)); g.add((izz, RDF.type, SDF.Izz)); g.add((izz, SDF.izzValue, Literal("0.04000000000000001")))
        return g, inert
    if kind == "visual":
        vis = URIRef("http://season.ai4sim/inst#v1")
        pose = URIRef("http://season.ai4sim/inst#vp1")
        geom = URIRef("http://season.ai4sim/inst#vg1")
        mesh = URIRef("http://season.ai4sim/inst#vm1")
        scale = URIRef("http://season.ai4sim/inst#vsc")
        uri = URIRef("http://season.ai4sim/inst#vu")
        g.add((vis, RDF.type, SDF.Visual))
        g.add((vis, SDF.visualName, Literal("sample_visual")))
        g.add((vis, SDF.hasPose, pose))
        g.add((pose, RDF.type, SDF.Pose))
        g.add((pose, SDF.poseValue, Literal("0 0 0 0 0 0")))
        g.add((vis, SDF.hasGeometry, geom))
        g.add((geom, RDF.type, SDF.Geometry))
        g.add((geom, SDF.hasMesh, mesh))
        g.add((mesh, RDF.type, SDF.Mesh))
        g.add((mesh, SDF.hasScale, scale))
        g.add((scale, RDF.type, SDF.Scale))
        g.add((scale, SDF.scaleValue, Literal("1 1 1")))
        g.add((mesh, SDF.hasUri, uri))
        g.add((uri, RDF.type, SDF.Uri))
        g.add((uri, SDF.uriValue, Literal("model://x500_base/meshes/default.dae")))
        return g, vis
    if kind == "joint":
        j = URIRef("http://season.ai4sim/inst#j1")
        parent = URIRef("http://season.ai4sim/inst#par")
        child = URIRef("http://season.ai4sim/inst#chi")
        axis = URIRef("http://season.ai4sim/inst#ax")
        xyz = URIRef("http://season.ai4sim/inst#xyz")
        limit = URIRef("http://season.ai4sim/inst#lim")
        low = URIRef("http://season.ai4sim/inst#low")
        up = URIRef("http://season.ai4sim/inst#up")
        dyn = URIRef("http://season.ai4sim/inst#dyn")
        sr = URIRef("http://season.ai4sim/inst#sr")
        ss = URIRef("http://season.ai4sim/inst#ss")
        g.add((j, RDF.type, SDF.Joint))
        g.add((j, SDF.jointName, Literal("rotor_0_joint")))
        g.add((j, SDF.jointType, Literal("revolute")))
        g.add((j, SDF.hasParent, parent)); g.add((parent, RDF.type, SDF.Parent)); g.add((parent, SDF.parentValue, Literal("base_link")))
        g.add((j, SDF.hasChild, child)); g.add((child, RDF.type, SDF.Child)); g.add((child, SDF.childValue, Literal("rotor_0")))
        g.add((j, SDF.hasAxis, axis)); g.add((axis, RDF.type, SDF.Axis))
        g.add((axis, SDF.hasXyz, xyz)); g.add((xyz, RDF.type, SDF.Xyz)); g.add((xyz, SDF.xyzValue, Literal("0 0 1")))
        g.add((axis, SDF.hasLimit, limit)); g.add((limit, RDF.type, SDF.Limit))
        g.add((limit, SDF.hasLower, low)); g.add((low, RDF.type, SDF.Lower)); g.add((low, SDF.lowerValue, Literal("-1e16")))
        g.add((limit, SDF.hasUpper, up)); g.add((up, RDF.type, SDF.Upper)); g.add((up, SDF.upperValue, Literal("1e16")))
        g.add((axis, SDF.hasDynamics, dyn)); g.add((dyn, RDF.type, SDF.Dynamics))
        g.add((dyn, SDF.hasSpringReference, sr)); g.add((sr, RDF.type, SDF.SpringReference)); g.add((sr, SDF.springReferenceValue, Literal("0")))
        g.add((dyn, SDF.hasSpringStiffness, ss)); g.add((ss, RDF.type, SDF.SpringStiffness)); g.add((ss, SDF.springStiffnessValue, Literal("0")))
        return g, j
    if kind == "motor_plugin":
        mp = URIRef("http://season.ai4sim/inst#mp")
        g.add((mp, RDF.type, SDF.MotorPlugin))
        g.add((mp, SDF.pluginFilename, Literal("gz-sim-multicopter-motor-model-system")))
        g.add((mp, SDF.pluginName, Literal("gz::sim::systems::MulticopterMotorModel")))
        for p, v in [
            (SDF.motorPluginJointNameValue, "rotor_0_joint"),
            (SDF.motorPluginLinkNameValue, "rotor_0"),
            (SDF.motorPluginTurningDirectionValue, "ccw"),
            (SDF.motorPluginMotorNumberValue, "0"),
            (SDF.motorPluginTimeConstantUpValue, "0.0125"),
            (SDF.motorPluginTimeConstantDownValue, "0.025"),
            (SDF.motorPluginMaxRotVelocityValue, "1000.0"),
            (SDF.motorPluginMotorConstantValue, "8.54858e-06"),
            (SDF.motorPluginMomentConstantValue, "0.016"),
            (SDF.motorPluginCommandSubTopicValue, "command/motor_speed"),
            (SDF.motorPluginRotorDragCoefficientValue, "8.06428e-05"),
            (SDF.motorPluginRollingMomentCoefficientValue, "1e-06"),
            (SDF.motorPluginRotorVelocitySlowdownSimValue, "10"),
            (SDF.motorPluginMotorTypeValue, "velocity"),
        ]:
            g.add((mp, p, Literal(v)))
        return g, mp
    if kind == "standard_sensors":
        root = URIRef("http://season.ai4sim/inst#sensors")
        ap = URIRef("http://season.ai4sim/inst#ap")
        g.add((ap, RDF.type, SDF.Sensor))
        g.add((ap, SDF.sensorName, Literal("air_pressure_sensor")))
        g.add((ap, SDF.sensorType, Literal("air_pressure")))
        g.add((ap, SDF.GzFrameId, Literal("base_link")))
        g.add((ap, SDF.AlwaysOn, Literal("true")))
        g.add((ap, SDF.UpdateRate, Literal("80")))
        mg = URIRef("http://season.ai4sim/inst#mg")
        g.add((mg, RDF.type, SDF.Sensor))
        g.add((mg, SDF.sensorName, Literal("magnetometer_sensor")))
        g.add((mg, SDF.sensorType, Literal("magnetometer")))
        imu = URIRef("http://season.ai4sim/inst#imu")
        g.add((imu, RDF.type, SDF.Sensor))
        g.add((imu, SDF.sensorName, Literal("imu_sensor")))
        g.add((imu, SDF.sensorType, Literal("imu")))
        ns = URIRef("http://season.ai4sim/inst#ns")
        g.add((ns, RDF.type, SDF.Sensor))
        g.add((ns, SDF.sensorName, Literal("navsat_sensor")))
        g.add((ns, SDF.sensorType, Literal("navsat")))
        g.add((root, SDF.hasSensor, ap))
        g.add((root, SDF.hasSensor, mg))
        g.add((root, SDF.hasSensor, imu))
        g.add((root, SDF.hasSensor, ns))
        return g, root
    raise ValueError("unsupported kind")

def load_graph(path: str | None):
    g = Graph()
    if path:
        fmt = "xml" if path.endswith(".owl") or path.endswith(".rdf") else "turtle"
        g.parse(path, format=fmt)
    return g

def _strip_xml_comments(text: str) -> str:
    return re.sub(r"<!--[\s\S]*?-->", "", text)

def _indent_lines(text: str, indent: str) -> str:
    lines = text.splitlines()
    return "\n".join([(indent + l if l.strip() else l) for l in lines])

def _extract_defaults_from_comment(comment_text: str) -> dict:
    out = {}
    if not comment_text:
        return out
    for m in re.finditer(r"Default\s+([A-Za-z_][\w]*)\s*:\s*(.+)", comment_text):
        out[m.group(1).strip()] = m.group(2).strip()
    return out

def _expand_component_snippet(kind: str, defaults: dict, slot_token: str) -> str:
    if kind == "inertial":
        mass = defaults.get("mass", "2.0")
        ixx = defaults.get("ixx", "0")
        iyy = defaults.get("iyy", "0")
        izz = defaults.get("izz", "0")
        xml_text = _normalize_fragment(generate_xml("inertial", Graph(), None))
        xml_text = re.sub(r"<mass>.*?</mass>", f"<mass>{mass}</mass>", xml_text, flags=re.DOTALL)
        xml_text = re.sub(r"<ixx>.*?</ixx>", f"<ixx>{ixx}</ixx>", xml_text)
        xml_text = re.sub(r"<iyy>.*?</iyy>", f"<iyy>{iyy}</iyy>", xml_text)
        xml_text = re.sub(r"<izz>.*?</izz>", f"<izz>{izz}</izz>", xml_text)
        return xml_text
    if kind == "visual":
        pose = defaults.get("pose", "0 0 0 0 0 0")
        uri = defaults.get("uri", "model://x500_base/meshes/default.dae")
        scale = defaults.get("scale", "1 1 1")
        xml_text = _normalize_fragment(generate_xml("visual", Graph(), None))
        visual_name = slot_token
        xml_text = re.sub(r'<visual\s+name="[^"]*"', f'<visual name="{visual_name}"', xml_text)
        xml_text = re.sub(r"<pose>.*?</pose>", f"<pose>{pose}</pose>", xml_text, flags=re.DOTALL)
        xml_text = re.sub(r"<scale>.*?</scale>", f"<scale>{scale}</scale>", xml_text, flags=re.DOTALL)
        xml_text = re.sub(r"<uri>.*?</uri>", f"<uri>{uri}</uri>", xml_text, flags=re.DOTALL)
        return xml_text
    if kind == "collision":
        pose = defaults.get("pose", "0 0 0 0 0 0")
        size = defaults.get("size", "1 1 1")
        xml_text = _normalize_fragment(generate_xml("collision", Graph(), None))
        collision_name = slot_token
        xml_text = re.sub(r'<collision\s+name="[^"]*"', f'<collision name="{collision_name}"', xml_text)
        xml_text = re.sub(r"<pose>.*?</pose>", f"<pose>{pose}</pose>", xml_text, flags=re.DOTALL)
        xml_text = re.sub(r"<size>.*?</size>", f"<size>{size}</size>", xml_text, flags=re.DOTALL)
        return xml_text
    if kind == "standard_sensors":
        xml_text = Path("/home/zhike/Season/AI4Sim/generator/ontology/standard_sensors.sdf").read_text(encoding="utf-8")
        xml_text = _strip_xml_comments(xml_text).strip()
        xml_text = xml_text.replace("${airPressureName}", "air_pressure_sensor")
        xml_text = xml_text.replace("${magnetometerName}", "magnetometer_sensor")
        xml_text = xml_text.replace("${imuName}", "imu_sensor")
        xml_text = xml_text.replace("${navsatName}", "navsat_sensor")
        return _normalize_fragment(xml_text)
    if kind == "motor_plugin":
        xml_text = _normalize_fragment(generate_xml("motor_plugin", Graph(), None))
        return xml_text
    raise ValueError(f"unsupported component kind: {kind}")

def _framework_placeholder_class_name(token: str) -> str:
    if not token:
        return ""
    return token[0].upper() + token[1:] + "Placeholder"

def generate_framework_from_template(framework: str, owl_path: str, expand: bool) -> str:
    template_path = f"/home/zhike/Season/AI4Sim/generator/ontology/{framework}.sdf"
    template_text = Path(template_path).read_text(encoding="utf-8")
    g = load_graph(owl_path)
    placeholder_classes = set()
    for cls in g.subjects(RDF.type, URIRef("http://www.w3.org/2002/07/owl#Class")):
        local = str(cls).split("#")[-1]
        if local.endswith("Placeholder"):
            placeholder_classes.add(local)

    lines = template_text.splitlines()
    out_lines = []
    pending_comment = ""
    in_comment = False
    comment_buf = []

    for line in lines:
        if "<!--" in line:
            in_comment = True
            comment_buf = [line]
            if "-->" in line:
                in_comment = False
                pending_comment = "\n".join(comment_buf)
                comment_buf = []
            out_lines.append(line if not expand else line)
            continue
        if in_comment:
            comment_buf.append(line)
            out_lines.append(line if not expand else line)
            if "-->" in line:
                in_comment = False
                pending_comment = "\n".join(comment_buf)
                comment_buf = []
            continue

        m = re.search(r"\$\{([A-Za-z0-9_]+)\}", line)
        if not m:
            out_lines.append(line)
            continue

        token = m.group(1)
        placeholder_class = _framework_placeholder_class_name(token)
        if placeholder_class not in placeholder_classes:
            out_lines.append(line)
            continue

        if not expand:
            out_lines.append(line)
            continue

        defaults = _extract_defaults_from_comment(pending_comment)
        pending_comment = ""

        if "Inertial" in placeholder_class:
            kind = "inertial"
        elif "Collision" in placeholder_class:
            kind = "collision"
        elif "Visual" in placeholder_class:
            kind = "visual"
        elif placeholder_class == "StandardSensorsPlaceholder":
            kind = "standard_sensors"
        elif placeholder_class == "MotorPluginsPlaceholder":
            kind = "motor_plugin"
        else:
            out_lines.append(line)
            continue

        indent = re.match(r"^(\s*)", line).group(1)
        snippet = _expand_component_snippet(kind, defaults, token)
        out_lines.append(_indent_lines(snippet, indent))

    expanded_text = "\n".join(out_lines)

    if framework == "model_framework" and expand:
        expanded_text = expanded_text.replace("${baseModelURI}", "model://x500_base")
        if "${motorPlugins}" in expanded_text:
            plugins = []
            for i, direction in [(0, "ccw"), (1, "ccw"), (2, "cw"), (3, "cw")]:
                plugin = _normalize_fragment(generate_xml("motor_plugin", Graph(), None))
                plugin = re.sub(r"<jointName>.*?</jointName>", f"<jointName>rotor_{i}_joint</jointName>", plugin, flags=re.DOTALL)
                plugin = re.sub(r"<linkName>.*?</linkName>", f"<linkName>rotor_{i}</linkName>", plugin, flags=re.DOTALL)
                plugin = re.sub(r"<turningDirection>.*?</turningDirection>", f"<turningDirection>{direction}</turningDirection>", plugin, flags=re.DOTALL)
                plugin = re.sub(r"<motorNumber>.*?</motorNumber>", f"<motorNumber>{i}</motorNumber>", plugin, flags=re.DOTALL)
                plugins.append(plugin)
            expanded_text = expanded_text.replace("${motorPlugins}", "\n".join(plugins))

    return expanded_text

def generate_xml(kind: str, g: Graph, subject: URIRef | None):
    if kind == "collision":
        if subject is None:
            g, subject = graph_from_inline_sample("collision")
        el = build_collision_element(g, subject)
        return ET.tostring(el, encoding="unicode")
    if kind == "inertial":
        if subject is None:
            g, subject = graph_from_inline_sample("inertial")
        el = build_inertial_element(g, subject)
        return ET.tostring(el, encoding="unicode")
    if kind == "visual":
        if subject is None:
            g, subject = graph_from_inline_sample("visual")
        vis = subject
        el = ET.Element("visual")
        for v in g.objects(vis, SDF.visualName):
            el.set("name", str(v))
        for p in g.objects(vis, SDF.hasPose):
            p_el = ET.SubElement(el, "pose")
            for val in g.objects(p, SDF.poseValue):
                _write_el_text(p_el, str(val))
        for geom in g.objects(vis, SDF.hasGeometry):
            ge_el = ET.SubElement(el, "geometry")
            for mesh in g.objects(geom, SDF.hasMesh):
                m_el = ET.SubElement(ge_el, "mesh")
                for sc in g.objects(mesh, SDF.hasScale):
                    sc_el = ET.SubElement(m_el, "scale")
                    for val in g.objects(sc, SDF.scaleValue):
                        _write_el_text(sc_el, str(val))
                for u in g.objects(mesh, SDF.hasUri):
                    u_el = ET.SubElement(m_el, "uri")
                    for val in g.objects(u, SDF.uriValue):
                        _write_el_text(u_el, str(val))
        return ET.tostring(el, encoding="unicode")
    if kind == "joint":
        if subject is None:
            g, subject = graph_from_inline_sample("joint")
        j = subject
        el = ET.Element("joint")
        for v in g.objects(j, SDF.jointName):
            el.set("name", str(v))
        for v in g.objects(j, SDF.jointType):
            el.set("type", str(v))
        for par in g.objects(j, SDF.hasParent):
            p_el = ET.SubElement(el, "parent")
            for val in g.objects(par, SDF.parentValue):
                _write_el_text(p_el, str(val))
        for chi in g.objects(j, SDF.hasChild):
            c_el = ET.SubElement(el, "child")
            for val in g.objects(chi, SDF.childValue):
                _write_el_text(c_el, str(val))
        for ax in g.objects(j, SDF.hasAxis):
            ax_el = ET.SubElement(el, "axis")
            for xyz in g.objects(ax, SDF.hasXyz):
                xyz_el = ET.SubElement(ax_el, "xyz")
                for val in g.objects(xyz, SDF.xyzValue):
                    _write_el_text(xyz_el, str(val))
            for lim in g.objects(ax, SDF.hasLimit):
                lim_el = ET.SubElement(ax_el, "limit")
                for low in g.objects(lim, SDF.hasLower):
                    low_el = ET.SubElement(lim_el, "lower")
                    for val in g.objects(low, SDF.lowerValue):
                        _write_el_text(low_el, str(val))
                for up in g.objects(lim, SDF.hasUpper):
                    up_el = ET.SubElement(lim_el, "upper")
                    for val in g.objects(up, SDF.upperValue):
                        _write_el_text(up_el, str(val))
            for dyn in g.objects(ax, SDF.hasDynamics):
                d_el = ET.SubElement(ax_el, "dynamics")
                for sr in g.objects(dyn, SDF.hasSpringReference):
                    sr_el = ET.SubElement(d_el, "spring_reference")
                    for val in g.objects(sr, SDF.springReferenceValue):
                        _write_el_text(sr_el, str(val))
                for ss in g.objects(dyn, SDF.hasSpringStiffness):
                    ss_el = ET.SubElement(d_el, "spring_stiffness")
                    for val in g.objects(ss, SDF.springStiffnessValue):
                        _write_el_text(ss_el, str(val))
        return ET.tostring(el, encoding="unicode")
    if kind == "motor_plugin":
        if subject is None:
            g, subject = graph_from_inline_sample("motor_plugin")
        mp = subject
        el = ET.Element("plugin")
        for v in g.objects(mp, SDF.pluginFilename):
            el.set("filename", str(v))
        for v in g.objects(mp, SDF.pluginName):
            el.set("name", str(v))
        def _sub(tag, prop):
            for vv in g.objects(mp, prop):
                t = ET.SubElement(el, tag)
                _write_el_text(t, str(vv))
        _sub("jointName", SDF.motorPluginJointNameValue)
        _sub("linkName", SDF.motorPluginLinkNameValue)
        _sub("turningDirection", SDF.motorPluginTurningDirectionValue)
        _sub("motorNumber", SDF.motorPluginMotorNumberValue)
        _sub("timeConstantUp", SDF.motorPluginTimeConstantUpValue)
        _sub("timeConstantDown", SDF.motorPluginTimeConstantDownValue)
        _sub("maxRotVelocity", SDF.motorPluginMaxRotVelocityValue)
        _sub("motorConstant", SDF.motorPluginMotorConstantValue)
        _sub("momentConstant", SDF.motorPluginMomentConstantValue)
        _sub("commandSubTopic", SDF.motorPluginCommandSubTopicValue)
        _sub("rotorDragCoefficient", SDF.motorPluginRotorDragCoefficientValue)
        _sub("rollingMomentCoefficient", SDF.motorPluginRollingMomentCoefficientValue)
        _sub("rotorVelocitySlowdownSim", SDF.motorPluginRotorVelocitySlowdownSimValue)
        _sub("motorType", SDF.motorPluginMotorTypeValue)
        return ET.tostring(el, encoding="unicode")
    if kind == "standard_sensors":
        if subject is None:
            g, subject = graph_from_inline_sample("standard_sensors")
        root = subject
        out_parts = []
        for s in g.objects(root, SDF.hasSensor):
            el = ET.Element("sensor")
            for v in g.objects(s, SDF.sensorName):
                el.set("name", str(v))
            for v in g.objects(s, SDF.sensorType):
                el.set("type", str(v))
            for v in g.objects(s, SDF.GzFrameId):
                gf = ET.SubElement(el, "gz_frame_id"); _write_el_text(gf, str(v))
            for v in g.objects(s, SDF.AlwaysOn):
                ao = ET.SubElement(el, "always_on"); _write_el_text(ao, str(v))
            for v in g.objects(s, SDF.UpdateRate):
                ur = ET.SubElement(el, "update_rate"); _write_el_text(ur, str(v))
            out_parts.append(ET.tostring(el, encoding="unicode"))
        return "\n".join(out_parts)
    if kind == "model_base":
        xml_text = generate_framework_from_template("model_base", "/home/zhike/Season/AI4Sim/generator/ontology/model_base.owl", expand=False)
        return xml_text
    if kind == "model_framework":
        xml_text = generate_framework_from_template("model_framework", "/home/zhike/Season/AI4Sim/generator/ontology/model_framework.owl", expand=False)
        return xml_text
    raise ValueError("unsupported kind")

def unified_diff(a: str, b: str, a_label: str, b_label: str):
    a_lines = _normalize_xml(a).splitlines()
    b_lines = _normalize_xml(b).splitlines()
    return "\n".join(difflib.unified_diff(a_lines, b_lines, fromfile=a_label, tofile=b_label, lineterm=""))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["collision", "inertial", "visual", "joint", "motor_plugin", "standard_sensors", "model_base", "model_framework"])
    p.add_argument("--input", type=str)
    p.add_argument("--subject", type=str)
    p.add_argument("--compare", type=str)
    p.add_argument("--expand", action="store_true")
    p.add_argument("--owl", type=str)
    p.add_argument("--strip-comments", action="store_true")
    args = p.parse_args()
    if args.kind in {"model_base", "model_framework"}:
        owl_path = args.owl or f"/home/zhike/Season/AI4Sim/generator/ontology/{args.kind}.owl"
        xml_text = generate_framework_from_template(args.kind, owl_path, expand=bool(args.expand))
    else:
        g = load_graph(args.input) if args.input else Graph()
        subj = URIRef(args.subject) if args.subject else None
        xml_text = generate_xml(args.kind, g, subj)
    out_pretty = _normalize_xml(xml_text)
    try:
        print(out_pretty)
    except BrokenPipeError:
        return
    if args.compare:
        target_text = Path(args.compare).read_text(encoding="utf-8")
        if args.strip_comments:
            target_text = _strip_xml_comments(target_text)
            out_pretty_cmp = _strip_xml_comments(out_pretty)
        else:
            out_pretty_cmp = out_pretty
        diff = unified_diff(out_pretty_cmp, target_text, "owl_generated", args.compare)
        try:
            print("\n=== DIFF ===")
            print(diff)
        except BrokenPipeError:
            return

if __name__ == "__main__":
    main()
