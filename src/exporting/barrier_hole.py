"""Export glass/grating hole configurations."""
from srctools import Keyvalues
import trio

from packages import BarrierHole
import utils

from . import STEPS, ExportData, StepResource


@STEPS.add_step(prereq=[], results=[StepResource.VCONF_DATA])
async def step_barrier_hole(exp_data: ExportData) -> None:
    """Export glass/grating hole configurations."""
    async with trio.open_nursery() as nursery:
        configs = [
            (hole, utils.Result(nursery, hole.variant_conf))
            for hole in exp_data.packset.all_obj(BarrierHole)
        ]
    conf_block = Keyvalues('BarrierHoles', [])

    for hole, variant_conf in configs:
        kv = variant_conf()
        kv.name = 'Variants'

        conf_block.append(Keyvalues(hole.id, [
            Keyvalues('Footprint', hole.footprint_id),
            Keyvalues('error_shape', hole.error_shape),
            kv,
        ]))

    if conf_block:
        exp_data.vbsp_conf.append(conf_block)
