"""StyleVPK allows specifying a set of files that will be added to a DLC3 VPK.

This allows altering the in-editor wall textures, as well as a few others.
"""
from __future__ import annotations
from typing import Any
from typing_extensions import Self
import os

from srctools import FileSystem
import srctools.logger

from packages import PakObject, ParseData

LOGGER = srctools.logger.get_logger(__name__, alias='packages.styleVPK')


class StyleVPK(PakObject):
    """A set of VPK files used for styles.

    These are copied into _dlc3, allowing changing the in-editor wall
    textures.
    """
    def __init__(self, vpk_id: str, filesys: FileSystem[Any], directory: str) -> None:
        """Initialise a StyleVPK object."""
        self.id = vpk_id
        self.fsys = filesys
        self.dir = directory

    @classmethod
    async def parse(cls, data: ParseData) -> Self:
        """Read the VPK file from the package."""
        vpk_name = data.info['filename']

        source_folder = os.path.normpath('vpk/' + vpk_name)

        # At least one exists?
        if not any(data.fsys.walk_folder(source_folder)):
            raise Exception(
                f'VPK object "{data.id}" has no associated files!'
            )

        return cls(data.id, data.fsys, source_folder)
