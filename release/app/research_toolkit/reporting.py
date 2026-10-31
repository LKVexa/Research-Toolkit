"""Portable aggregate-only report. User text is escaped; no scripts or remote assets."""
import html
import json


def render(public):
    result=public['result']; protocol=public['protocol']['protocol']; summary=result.get('summary',{})
    esc=lambda x:html.escape(str(x),quote=True)
    scores=''
    if summary:
        scores=f'''<div class="cards"><section><span>Method</span><strong>{esc(summary['candidate_score'])}</strong></section>
        <section><span>Baseline</span><strong>{esc(summary['baseline_score'])}</strong></section>
        <section><span>Scored observations</span><strong>{esc(summary['sample_count'])}</strong></section></div>
        <p>Metric: {esc(summary['metric'])}; direction: {esc(summary['direction'])}. Directional improvement: {esc(summary['mean_improvement'])}.
        Absolute comparison tolerance: {esc(summary['tolerance'])}.</p>
        <p>{esc(summary['repetitions'])} deterministic replay(s). Repeated runs do not increase the independent sample count.</p>'''
    rows=''.join(f'<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>' for label,value in [
        ('Execution',result['execution']),('Implementation checks',result['implementation_checks']),
        ('Observed comparison',result['comparison']),('Source-paper validation',result['source_claim']),
        ('Frozen protocol',result['protocol_id']),('Protocol SHA-256',result['protocol_sha256']),
        ('Package digest',result['package_manifest_sha256']),('Run receipt SHA-256',public['receipt_sha256'])])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
    <title>Research report · {esc(result['run_id'])}</title><style>
    body{{margin:0;background:#f3f5f6;color:#182b34;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1000px;margin:48px auto;padding:32px}}
    .eyebrow{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#526c78}}h1{{font-size:38px;line-height:1.2;margin:10px 0 28px}}
    .banner{{padding:20px 24px;background:#153d49;color:white;border-radius:10px}}.cards{{display:flex;gap:16px;margin:24px 0}}
    section{{flex:1;background:white;padding:22px;border-radius:10px;border:1px solid #dce5e8}}span{{display:block;font-size:14px;color:#526c78}}strong{{display:block;font-size:30px;overflow-wrap:anywhere}}
    table{{border-collapse:collapse;width:100%;margin:28px 0;background:white}}td,th{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #dce5e8;overflow-wrap:anywhere}}th{{width:230px}}
    .note{{border-left:4px solid #9aaeb7;padding:14px 20px;background:#e8eef1}}footer{{font-size:13px;color:#526c78;margin-top:35px}}
    @media(max-width:650px){{main{{margin:10px;padding:18px}}h1{{font-size:28px}}.cards{{display:block}}section{{margin:10px 0}}th{{width:35%}}}}
    </style></head><body><main><div class="eyebrow">Research replication &amp; benchmarking toolkit</div>
    <h1>{esc(result['protocol_id'])}</h1><div class="banner">Observed comparison: <b>{esc(result['comparison'])}</b><br>
    Execution and scientific interpretation are recorded separately.</div>{scores}
    <h2>Frozen hypothesis</h2><p>{esc(protocol['hypothesis'])}</p><table>{rows}</table>
    <div class="note">This is a descriptive fixture or authored benchmark result. A positive comparison is not a statistical significance claim or a completed paper replication.
    Final labels, row-level losses and raw predictions are omitted from this public report. Full evidence remains in the local run state.</div>
    <p>{esc(result.get('reason') or result.get('scope',''))}</p><footer>Run {esc(result['run_id'])} · Completed {esc(result['finished_at'])} · No network assets or executable report scripts.</footer>
    </main></body></html>'''
