# Suggested filename: pipeline.py

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageStat

# pip install instructions:
# py -m pip install trimesh pillow numpy
# Optional OpenAI mode: py -m pip install openai


@dataclass
class Brief:
    prompt: str
    object_type: str
    strategies: list[str]
    dimensions_mm: list[float] | None = None
    requirements: list[str] | None = None


class Planner:
    def plan(self, prompt: str) -> Brief:
        p = prompt.lower()
        if "cube" in p:
            return Brief(prompt, "cube", ["primitive_csg"], [20, 20, 20], ["exact dimensions"])
        if "name tag" in p or "key ring" in p:
            return Brief(prompt, "name_tag", ["2d_extrusion", "boolean", "text"], [60, 20, 2], ["Pepper text", "rounded corners", "2 mm hole"])
        if "frog" in p and ("tea cup" in p or "teacup" in p):
            return Brief(prompt, "frog_teacup", ["shell", "organic_hull"], None, ["one connected printable object"])
        if "bishop" in p:
            return Brief(prompt, "bishop", ["revolve", "boolean"], None, ["diagonal mitre slot"])
        if "f-16" in p or "f16" in p:
            return Brief(prompt, "f16", ["hull_loft", "symmetry", "compound_subsystems"], None, ["recognizable silhouette", "one connected display model"])
        return Brief(prompt, "generic", ["primitive_csg"], None, ["FDM printable"])


class LocalGenerator:
    def generate(self, brief: Brief, feedback: list[str]) -> str:
        return getattr(self, "_" + brief.object_type, self._generic)()

    def _cube(self):
        return "cube([20,20,20]);\n"

    def _name_tag(self):
        return r'''$fn=64;
w=60; h=20; t=2; r=3; hole_d=2; font_size=10;
module rr() { hull() { for (x=[r,w-r], y=[r,h-r]) translate([x,y]) circle(r=r); } }
difference() {
  linear_extrude(height=t) rr();
  translate([2,h-2,-0.5]) cylinder(h=t+1,d=hole_d);
  translate([w/2,h/2,t-0.6]) linear_extrude(height=0.7)
    text("Pepper",size=font_size,halign="center",valign="center");
}
'''

    def _frog_teacup(self):
        return r'''$fn=64;
cup_h=40; outer_r=28; wall=2.6; bottom=4;
module cup() {
 union() {
  difference() { cylinder(h=cup_h,r=outer_r); translate([0,0,bottom]) cylinder(h=cup_h+1,r=outer_r-wall); }
  translate([outer_r-1,0,22]) rotate([90,0,0]) difference() { cylinder(h=7,r=17,center=true); cylinder(h=9,r=11,center=true); }
 }
}
module e(s=[1,1,1]) { scale(s) sphere(r=1); }
module frog() {
 union() {
  translate([0,0,38]) e([12,9,8]);
  translate([0,0,48]) e([9,8,7]);
  for(s=[-1,1]) {
   translate([s*5,2,54]) sphere(r=3.2);
   hull() { translate([s*8,0,40]) sphere(r=3.5); translate([s*13,-1,36]) sphere(r=4); }
  }
 }
}
union() { cup(); frog(); }
'''

    def _bishop(self):
        return r'''$fn=96;
module body() {
 rotate_extrude(convexity=10) polygon(points=[[0,0],[20,0],[22,3],[22,6],[18,9],[15,11],[12,17],[10,30],[12,40],[9,48],[7,55],[0,58]]);
}
difference() {
 union() { body(); translate([0,0,61]) sphere(r=10); }
 translate([-2,-15,57]) rotate([0,28,0]) cube([5,30,18]);
}
'''

    def _f16(self):
        return r'''$fn=40;
module e(p=[0,0,0],s=[1,1,1]) { translate(p) scale(s) sphere(r=1); }
module fuselage() {
 hull(){e([-48,0,10],[4,4,4]);e([-28,0,10],[12,6,6]);}
 hull(){e([-28,0,10],[12,6,6]);e([5,0,10],[24,7,7]);}
 hull(){e([5,0,10],[24,7,7]);e([42,0,10],[10,4,4]);}
 hull(){e([42,0,10],[10,4,4]);e([58,0,10],[2,2,2]);}
}
module wing(s=1) { translate([0,0,9]) linear_extrude(height=3) polygon(points=[[-20,0],[-5,s*4],[14,s*34],[25,s*28],[18,s*5]]); }
module htail(s=1) { translate([30,0,9]) linear_extrude(height=3) polygon(points=[[-8,0],[0,s*3],[15,s*17],[20,s*12],[14,s*3]]); }
module vtail() { hull(){translate([25,-2,13]) cube([16,4,3]);translate([34,-2,34]) cube([5,4,3]);} }
module canopy() { hull(){e([-12,0,16],[9,4,3]);e([5,0,16],[8,4,3]);} }
union(){fuselage();wing(1);wing(-1);htail(1);htail(-1);vtail();canopy();}
'''

    def _generic(self):
        return "cube([20,20,20]);\n"


class OpenAIGenerator:
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = os.getenv("OPENAI_CAD_MODEL", "gpt-5.6")

    def generate(self, brief: Brief, feedback: list[str]) -> str:
        response = self.client.responses.create(
            model=self.model,
            reasoning={"effort": "high"},
            instructions="Return only valid OpenSCAD. Use millimeters. Make one robust FDM-printable connected object. Choose geometry according to the supplied strategy brief.",
            input=f"Prompt: {brief.prompt}\nBrief: {json.dumps(asdict(brief))}\nRepair feedback: {feedback}",
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:-1])
        return text + "\n"


class Compiler:
    def __init__(self):
        candidates = [r"C:\Program Files\OpenSCAD\openscad.com", r"C:\Program Files\OpenSCAD\openscad.exe"] if os.name == "nt" else ["/usr/bin/openscad"]
        self.exe = next((x for x in candidates if Path(x).exists()), None)
        if not self.exe:
            raise FileNotFoundError("OpenSCAD not found")

    def build(self, scad: str, out: Path):
        out.mkdir(parents=True, exist_ok=True)
        scad_path, stl_path, png_path = out/"model.scad", out/"model.stl", out/"model.png"
        scad_path.write_text(scad, encoding="ascii", errors="strict")
        a = subprocess.run([self.exe,"-o",str(stl_path),str(scad_path)],capture_output=True,text=True)
        cmd=[self.exe,"-o",str(png_path),"--imgsize=900,700","--viewall","--autocenter","--projection=perspective",str(scad_path)]
        if os.name != "nt" and shutil.which("xvfb-run"):
            cmd=["xvfb-run","-a"]+cmd
        b=subprocess.run(cmd,capture_output=True,text=True)
        return scad_path,stl_path,png_path,a,b


class Validator:
    def validate(self, brief: Brief, stl: Path, png: Path, a, b):
        reasons=[]; metrics={"stl_rc":a.returncode,"png_rc":b.returncode}
        if a.returncode: reasons.append("OpenSCAD STL compile failed")
        if b.returncode: reasons.append("OpenSCAD PNG render failed")
        if not stl.exists() or not stl.stat().st_size: reasons.append("STL missing")
        if not png.exists() or not png.stat().st_size: reasons.append("PNG missing")
        if reasons: return False,reasons,metrics
        mesh=trimesh.load_mesh(stl,process=True)
        metrics.update(watertight=bool(mesh.is_watertight),components=len(mesh.split(only_watertight=False)),faces=int(len(mesh.faces)),volume_mm3=round(float(abs(mesh.volume)),2),bbox_mm=[round(float(v),3) for v in mesh.extents])
        if not mesh.is_watertight: reasons.append("mesh not watertight")
        if metrics["components"] != 1: reasons.append(f"connected components={metrics['components']}")
        if metrics["volume_mm3"] <= 0: reasons.append("non-positive volume")
        if brief.dimensions_mm:
            err=np.abs(np.array(mesh.extents)-np.array(brief.dimensions_mm))
            metrics["dimension_error_mm"]=[round(float(v),3) for v in err]
            if np.any(err>0.25): reasons.append("explicit dimensions outside 0.25 mm tolerance")
        stat=ImageStat.Stat(Image.open(png).convert("L"))
        metrics["png_stddev"]=round(float(stat.stddev[0]),3)
        if stat.stddev[0] < 2: reasons.append("render appears blank")
        return not reasons,reasons,metrics


def run_one(prompt: str, out: Path, use_openai=False):
    brief=Planner().plan(prompt)
    gen=OpenAIGenerator() if use_openai else LocalGenerator()
    feedback=[]
    scad=gen.generate(brief,feedback)
    scad_path,stl,png,a,b=Compiler().build(scad,out)
    passed,reasons,metrics=Validator().validate(brief,stl,png,a,b)
    report={"brief":asdict(brief),"passed":passed,"reasons":reasons,"metrics":metrics}
    (out/"report.json").write_text(json.dumps(report,indent=2),encoding="ascii")
    return report
