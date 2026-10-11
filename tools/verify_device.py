"""Hardware protocol checks with an explicit test host. Quit FlowSight first.

These fixtures verify the ESP32 transport and rendering; they do not verify a
running desktop app or the physical touch sensor. No desktop tracking is changed.
"""
import argparse
import json
from pathlib import Path
import time
from device import Device


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port')
    parser.add_argument('--output', type=Path, default=Path('.local/device-verification.json'))
    parser.add_argument('--capture-dir', type=Path)
    args = parser.parse_args()
    device = Device(args.port)
    checks = []
    state = dict(language='es', mode='normal', mode_label='Normal', kind='Registrado hoy',
                 clock='01:47:22', status='Listo', phase='ready', total_seconds=6442,
                 goal_seconds=21600, goal_label='Objetivo diario', goal_value='6 horas',
                 context='Calendario conectado', primary_action='start', primary_label='Iniciar registro',
                 primary_enabled=True, stop_enabled=False, mode_enabled=True, busy=False)

    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print('PASS: ' + name, flush=True)

    def rejects(cmd, error, **kwargs):
        try:
            device.request(cmd, **kwargs)
        except RuntimeError as exc:
            check(str(exc) == error, f'{cmd}: {error}')
        else:
            raise AssertionError(f'{cmd} should be rejected')

    def sync(**kwargs):
        state.update(kwargs)
        device.request('sync', state=state)

    try:
        device.request('home')
        status = device.request('status')
        check(status['protocol'] == 2 and status['version'] == '0.2.0', 'compatible firmware identity')
        sync()
        status = device.request('status')
        check(status['clock'] == '01:47:22' and status['goal_seconds'] == 21600, 'app time and daily goal mirrored exactly')
        check(status['language'] == 'es' and status['primary_action'] == 'start', 'Spanish app state received')
        if args.capture_dir:
            device.capture(args.capture_dir / 'device-screen.png')
        device.events.clear()
        device.request('tap', x=105, y=213)
        controls = [event for event in device.events if event.get('event') == 'control']
        check(len(controls) == 1 and controls[0]['action'] == 'start', 'button sends one explicit start request')
        status = device.request('status')
        check(status['phase'] == 'ready' and status['clock'] == '01:47:22', 'button does not optimistically start a device timer')
        rejects('tap', 'no_button', x=105, y=213)
        device.serial.write((json.dumps(dict(cmd='ack', id=controls[0]['id'], ok=True))+'\n').encode())
        sync(phase='running', status='En directo', primary_action='pause', primary_label='Pausar registro', stop_enabled=True)
        device.request('tap', x=105, y=213)
        controls = [event for event in device.events if event.get('event') == 'control']
        check(controls[-1]['action'] == 'pause', 'app state changes the physical action to pause')
        device.serial.write((json.dumps(dict(cmd='ack', id=controls[-1]['id'], ok=True))+'\n').encode())
        sync(language='en', kind='Recorded today', status='Paused', phase='paused', goal_label='Daily goal',
             goal_value='6 hours', context='Calendar connected', primary_action='resume', primary_label='Resume tracking')
        check(device.request('status')['language'] == 'en', 'language changes without reflashing')
        device.request('tap', x=265, y=25)
        if args.capture_dir:
            device.capture(args.capture_dir / 'settings-en.png')
        device.request('home')
        sync(mode='pomodoro', mode_label='Pomodoro', clock='04:59', kind='Break', phase='break',
             primary_action='end_break', primary_label='End break')
        check(device.request('status')['clock'] == '04:59', 'Pomodoro clock comes from the host')
        if args.capture_dir:
            device.capture(args.capture_dir / 'pomodoro-en.png')
        rejects('sync', 'invalid_snapshot', state={'clock': '99:99'})
        rejects('reset', 'unknown_command')
        # An oversized line is discarded as a whole, including any JSON tail.
        device.serial.write(b'x'*4200 + b'{"cmd":"home"}\n')
        time.sleep(0.15)
        check(device.request('status')['clock'] == '04:59', 'oversized input does not corrupt the snapshot')
        time.sleep(5.1)
        status = device.request('status')
        check(not status['connected'] and not status['primary_enabled'] and status['clock'] == '04:59',
              'disconnect freezes last clock and disables controls')
        rejects('tap', 'no_button', x=105, y=213)
        if args.capture_dir:
            device.capture(args.capture_dir / 'offline-en.png')
        sync(language='es', mode='normal', mode_label='Normal', clock='01:47:22', kind='Registrado hoy',
             status='Listo', phase='ready', goal_label='Objetivo diario', goal_value='6 horas',
             context='Calendario conectado', primary_action='start', primary_label='Iniciar registro', stop_enabled=False)
        check(device.request('status')['connected'], 'fresh snapshot reconnects automatically')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'fixture_host': True, 'checks': checks, 'passed': len(checks)}, indent=2)+'\n')
    finally:
        device.close()


if __name__ == '__main__':
    main()
