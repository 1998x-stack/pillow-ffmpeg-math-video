"""Release gate: tests -> symbolic and shape preflight -> real-video postflight -> SHA256 manifest."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from render_video import MODEL, ease
from verifier import run_preflight
from visual_verifier import main as visual_main
BASE=Path(__file__).resolve().parent

def main():
    subprocess.run([sys.executable,'-m','pytest','-q',str(BASE/'test_verified_video.py')],check=True,cwd=BASE)
    checks=run_preflight(MODEL,ease)
    assert all(v.get('status')=='pass' for v in checks.values())
    video=BASE/'pythagoras_verified.mp4'
    visual_main(video,20261120)
    data=json.loads((BASE/'visual_verification.json').read_text())
    assert data['status']=='pass' and data['region_samples_passed']>=816
    assert data['video']['frames']==888
    files=['geometry_model.py','verifier.py','render_video.py','visual_verifier.py',
           'test_verified_video.py','README.md','visual_review.md','preflight.json',
           'render_stats.json','visual_verification.json','random_screenshot_contact_sheet.png',
           'pythagoras_verified.mp4']
    manifest={'status':'pass','tests':15,'symbolic':checks['symbolic'],
              'randomized':checks['randomized'],'motion':checks['animation'],
              'video':data['video'],'pixel_checks_passed':data['pixel_checks_passed'],
              'region_samples_passed':data['region_samples_passed'],
              'files':{}}
    for f in files:
        raw=(BASE/f).read_bytes()
        manifest['files'][f]={'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    (BASE/'release_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf8')
    print('RELEASE GATE: PASS; manifest:',BASE/'release_manifest.json')
if __name__=='__main__':main()