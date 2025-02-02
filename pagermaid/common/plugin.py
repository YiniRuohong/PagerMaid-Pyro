import contextlib
import json
import os
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel

from pagermaid import Config
from pagermaid.common.cache import cache
from pagermaid.utils import client

plugins_path = Path('plugins')


class LocalPlugin(BaseModel):
    name: str
    status: bool
    installed: bool = False
    version: Optional[float]

    @property
    def normal_path(self) -> Path:
        return plugins_path / f"{self.name}.py"

    @property
    def disabled_path(self) -> Path:
        return plugins_path / f"{self.name}.py.disabled"

    def remove(self):
        with contextlib.suppress(FileNotFoundError):
            os.remove(self.normal_path)
        with contextlib.suppress(FileNotFoundError):
            os.remove(self.disabled_path)

    def enable(self) -> bool:
        try:
            os.rename(self.disabled_path, self.normal_path)
            return True
        except Exception:
            return False

    def disable(self) -> bool:
        try:
            os.rename(self.normal_path, self.disabled_path)
            return True
        except Exception:
            return False


class RemotePlugin(LocalPlugin):
    section: str
    maintainer: str
    size: str
    supported: bool
    des: str
    ...

    async def install(self) -> bool:
        html = await client.get(f'{Config.GIT_SOURCE}{self.name}/main.py')
        if html.status_code == 200:
            self.remove()
            with open(plugins_path / f"{self.name}.py", mode="wb") as f:
                f.write(html.text.encode('utf-8'))
            return True
        return False


class PluginManager:
    def __init__(self):
        self.version_map = {}
        self.remote_version_map = {}
        self.plugins: List[LocalPlugin] = []
        self.remote_plugins: List[RemotePlugin] = []

    def load_local_version_map(self):
        if not os.path.exists(plugins_path / "version.json"):
            return
        with open(plugins_path / "version.json", 'r', encoding="utf-8") as f:
            self.version_map = json.load(f)

    def save_local_version_map(self):
        with open(plugins_path / "version.json", 'w', encoding="utf-8") as f:
            json.dump(self.version_map, f, indent=4)

    def get_local_version(self, name: str) -> Optional[float]:
        data = self.version_map.get(name)
        return float(data) if data else None

    def set_local_version(self, name: str, version: float) -> None:
        self.version_map[name] = version
        self.save_local_version_map()

    def get_plugin_install_status(self, name: str) -> bool:
        return name in self.version_map

    @staticmethod
    def get_plugin_load_status(name: str) -> bool:
        return bool(os.path.exists(plugins_path / f"{name}.py"))

    def remove_plugin(self, name: str) -> bool:
        if plugin := self.get_local_plugin(name):
            plugin.remove()
            if name in self.version_map:
                self.version_map.pop(name)
                self.save_local_version_map()
            return True
        return False

    def enable_plugin(self, name: str) -> bool:
        return plugin.enable() if (plugin := self.get_local_plugin(name)) else False

    def disable_plugin(self, name: str) -> bool:
        return plugin.disable() if (plugin := self.get_local_plugin(name)) else False

    def load_local_plugins(self) -> List[LocalPlugin]:
        self.load_local_version_map()
        self.plugins = []
        for plugin in os.listdir('plugins'):
            if plugin.endswith('.py') or plugin.endswith('.py.disabled'):
                plugin = plugin[:-12] if plugin.endswith('.py.disabled') else plugin[:-3]
                self.plugins.append(
                    LocalPlugin(
                        name=plugin,
                        installed=self.get_plugin_install_status(plugin),
                        status=self.get_plugin_load_status(plugin),
                        version=self.get_local_version(plugin)
                    )
                )
        return self.plugins

    def get_local_plugin(self, name: str) -> LocalPlugin:
        return next(filter(lambda x: x.name == name, self.plugins), None)

    @cache()
    async def load_remote_plugins(self) -> List[RemotePlugin]:
        plugin_list = await client.get(f"{Config.GIT_SOURCE}list.json")
        plugin_list = plugin_list.json()["list"]
        plugins = [
            RemotePlugin(
                **plugin,
                status=self.get_plugin_load_status(plugin["name"])
            ) for plugin in plugin_list
        ]
        self.remote_plugins = plugins
        self.remote_version_map = {}
        for plugin in plugins:
            self.remote_version_map[plugin.name] = plugin.version
        return plugins

    def get_remote_plugin(self, name: str) -> RemotePlugin:
        return next(filter(lambda x: x.name == name, self.remote_plugins), None)

    def plugin_need_update(self, name: str) -> bool:
        if local_version := self.get_local_version(name):
            if local_version == 0.0:
                return False
            if remote_version := self.remote_version_map.get(name):
                return local_version < remote_version
        return False

    async def install_remote_plugin(self, name: str) -> bool:
        if plugin := self.get_remote_plugin(name):
            if await plugin.install():
                self.set_local_version(name, plugin.version)
                return True
        return False

    async def update_remote_plugin(self, name: str) -> bool:
        if self.plugin_need_update(name):
            return await self.install_remote_plugin(name)
        return False

    async def update_all_remote_plugin(self) -> List[RemotePlugin]:
        updated_plugins = []
        for i in self.remote_plugins:
            if await self.update_remote_plugin(i.name):
                updated_plugins.append(i)
        return updated_plugins


plugin_manager = PluginManager()
