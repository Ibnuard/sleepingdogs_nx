"""Host test of actual startup repair, including missing files and failed writes."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory(prefix='sd-startup-config-') as temp:
        root=Path(temp);fixture=root/'fixture';fixture.mkdir();exe=root/'check'
        subprocess.run(['gcc','-std=gnu11','-O1','-g','-fsanitize=address,undefined',
            '-fno-sanitize-recover=all','-I'+str(ROOT/'src/launcher'),
            str(ROOT/'tests/startup_config.c'),'-o',str(exe)],check=True)
        output=subprocess.check_output([str(exe),str(fixture)],text=True).strip()
    report=dict(status='PASS',result=output,hardware_tested=False,
        sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),ROOT/'tests/startup_config.c',ROOT/'src/launcher/startup_config.h',ROOT/'src/launcher/startup_config_data.h')})
    (ROOT/'reports/startup-config-v0.1.1-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(output)

if __name__=='__main__':main()
