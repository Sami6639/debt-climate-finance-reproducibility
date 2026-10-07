"""Execute pure-Python review cells without network sockets; save real outputs."""
import os
os.environ.setdefault('IPYTHONDIR','/tmp/debt_ipython')
os.environ.setdefault('MPLCONFIGDIR','/tmp/debt_mpl')
from pathlib import Path
import nbformat
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
from nbconvert import HTMLExporter
root=Path(__file__).resolve().parent;os.chdir(root)
p=root/'reconstruction_review.ipynb';nb=nbformat.read(p,as_version=4)
shell=InteractiveShell.instance();count=0
for cell in nb.cells:
    if cell.cell_type!='code':continue
    count+=1
    with capture_output(stdout=True,stderr=True,display=True) as captured:
        result=shell.run_cell(cell.source,store_history=False)
    if result.error_before_exec or result.error_in_exec:
        raise RuntimeError(f'Notebook cell {count} failed: {result.error_before_exec or result.error_in_exec}')
    outputs=[]
    if captured.stdout:outputs.append(nbformat.v4.new_output('stream',name='stdout',text=captured.stdout))
    if captured.stderr:outputs.append(nbformat.v4.new_output('stream',name='stderr',text=captured.stderr))
    for rich in captured.outputs:
        outputs.append(nbformat.v4.new_output('display_data',data=rich.data,metadata=rich.metadata))
    cell.execution_count=count;cell.outputs=outputs
nb.metadata['execution']={'engine':'Sequential in-process IPython','status':'all code cells executed successfully','reason':'Socket-based Jupyter kernel startup is unavailable in this network-isolated runtime; no socket or permission workaround was used.'}
nbformat.validate(nb);nbformat.write(nb,p)
html,_=HTMLExporter().from_notebook_node(nb);p.with_suffix('.html').write_text(html)
print('Successfully executed',count,'code cells; rich outputs',sum(len(c.get('outputs',[])) for c in nb.cells))
