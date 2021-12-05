# coding: utf-8

import os
import yaml
import enum
import copy
import jinja2  # pip install Jinja2
from typing import Tuple
import pathlib


class ModuleKind(enum.Enum):
    NONE = 0
    EXECUTABLE = 1
    ARCHIVE = 2
    SHAREDOBJ = 3


# YAML class start
class ModuleDirectoriesItemSetting:

    def __init__(self, data):
        kind = data["kind"]
        path = data["path"]

        if kind == "EXECUTABLE":
            self._kind = ModuleKind.EXECUTABLE
        elif kind == "ARCHIVE":
            self._kind = ModuleKind.ARCHIVE
        elif kind == "SHAREDOBJ":
            self._kind = ModuleKind.SHAREDOBJ
        else:
            self._kind = ModuleKind.NONE

        self._path = path

    def get_kind(self) -> ModuleKind:
        return self._kind

    def get_path(self) -> str:
        return self._path


class ModuleDirectoriesSetting:

    def __init__(self, data):
        self.Item = []
        tmp = data["module_directories"]
        for item in tmp:
            self.Item.append(ModuleDirectoriesItemSetting(item))


class FileSettings:

    def __init__(self, data, key: str):
        self.extensions = []
        self.relation = []

        for item in data[key]["extensions"]:
            self.extensions.append(str(item))

        for item in data[key]["relation_include_keys"]:
            self.relation.append(str(item))


class CompilerSetting:

    def __init__(self, data):
        tmp = data["compiler"]
        self.cmake_version = tmp["cmake_version"]
        self.clang_iso = tmp["clang_iso"]
        self.cc = tmp["cc"]
        self.options = tmp["options"]


class YamlRoot:

    def __init__(self, data):
        root_data = data["CMakefileList"]
        self.file_encoding = root_data["file_encoding"]
        self.module_directories = ModuleDirectoriesSetting(root_data)
        self.header_file_settings = FileSettings(root_data, "header_file_settings")
        self.source_file_extensions = FileSettings(root_data, "source_file_extensions")
        self.compiler = CompilerSetting(root_data)
        self.exclude_dirs = []
        for item in root_data["exclude_dirs"]:
            self.exclude_dirs.append(item)
        self.exclude_files = []
        for item in root_data["exclude_files"]:
            self.exclude_files.append(item)


# YAML class end


class SourceTreeInfo (object):

    def __init__(self):
        self._path = ""
        self._name = ""
        self._isFile = False
        self._isDir = False
        self.Children = []
        self.RelationHeaderInfo = []
        self.RelationLibDirInfo = []
        self._module_kind = ModuleKind.NONE
        self._is_src_file = False
        self._is_head_file = False
        self._shozoku_module = object

    def set_path(self, path: str, root_path: str, setting: YamlRoot):
        self._path = path
        self._name = os.path.basename(path)
        self._isDir = os.path.isdir(path)
        self._isFile = os.path.isfile(path)
        for item in setting.module_directories.Item:
            full_path = os.path.join(root_path, item.get_path())
            if full_path == self._path:
                self._module_kind = item.get_kind()

        for ext in setting.source_file_extensions.extensions:
            if self.get_path().endswith(ext):
                self._is_src_file = True

        for ext in setting.header_file_settings.extensions:
            if self.get_path().endswith(ext):
                self._is_head_file = True

    def get_path(self):
        return self._path

    def get_isdir(self):
        return self._isDir

    def get_isfile(self):
        return self._isFile

    def get_name(self):
        return self._name

    def get_module_kind(self):
        return self._module_kind

    def get_is_src_file(self):
        return self._is_src_file

    def get_is_head_file(self):
        return self._is_head_file

    def set_shozoku_module(self, info: object):
        self._shozoku_module = info
        self._shozoku_module = _cast(SourceTreeInfo, self._shozoku_module)

    def get_shozoku_module(self):
        return self._shozoku_module


def execute():
    filename = "./setting.yml"
    setting = _load_setting(filename)

    # 対象ソースファイルの収集
    input_dir = input('探索対象のディレクトリを指定: ')
    root_info = _search_sources(input_dir, setting)

    # def print_recursive(info: SourceTreeInfo):
    #     for child_item in info.Children:
    #         print(child_item.get_path())
    #         print_recursive(child_item)
    #
    # print_recursive(root_info)

    # ソースファイルの解析
    def search_headerfile(info: SourceTreeInfo, search_root: SourceTreeInfo):
        setting_file_info_list = [
            setting.source_file_extensions.relation,
            setting.header_file_settings.relation
        ]

        if info.get_isfile():
            for setting_file_info in setting_file_info_list:
                if info.get_is_src_file():
                    with open(info.get_path(), "r", encoding=setting.file_encoding) as file:
                        src_lines = file.readlines()
                        for line in src_lines:
                            for inc_key in setting_file_info:
                                tmp_line = line.strip()
                                if tmp_line.startswith(inc_key):
                                    tmp_line = tmp_line.lstrip(inc_key)
                                    tmp_line = tmp_line.replace("\"", "")
                                    tmp_line = tmp_line.replace("<", "")
                                    tmp_line = tmp_line.replace(">", "")
                                    tmp_line = tmp_line.strip()
                                    is_contains = _is_contains_same_filename_recursive(tmp_line, root_info)
                                    if is_contains[0]:
                                        if not any(inf == is_contains[1] for inf in info.RelationHeaderInfo):
                                            info.RelationHeaderInfo.append(is_contains[1])

        for child_item in info.Children:
            search_headerfile(child_item, search_root)

    def set_header_files(info: SourceTreeInfo):
        search_headerfile(info, root_info)

        for child_item in info.Children:
            # print(child_item.get_path())
            set_header_files(child_item)

    set_header_files(root_info)

    _output_autogenerate(".", "template_cmakefilelist.j2", root_info, setting)


def _is_contains_same_filename_recursive(filename: str, search_base: SourceTreeInfo) -> Tuple[bool, SourceTreeInfo]:

    search_file = os.path.basename(search_base.get_path())
    if filename == search_file:
        return True, search_base

    for child_item in search_base.Children:
        tmp_result = _is_contains_same_filename_recursive(filename, child_item)
        if tmp_result[0]:
            return True, tmp_result[1]

    return False, search_base


def _is_contains_recursive(info: SourceTreeInfo, search_base: SourceTreeInfo) -> Tuple[bool, SourceTreeInfo]:
    if info.get_path() == search_base.get_path():
        return True, search_base

    for child_item in search_base.Children:
        tmp_result = _is_contains_recursive(info, child_item)
        if tmp_result[0]:
            return True, tmp_result[1]

    return False, info


def _cast(class_type, child_object) -> SourceTreeInfo:
    child_object.__class__ = class_type
    return child_object


def _load_setting(load_path: str):
    with open(load_path, "r", encoding="utf-8") as file:
        tmp = yaml.safe_load(file)

    #  _cast(YamlRoot, tmp)
    ret = YamlRoot(tmp)
    return ret


def _create_source_tree_info(path: str, root_path: str, setting: YamlRoot) -> SourceTreeInfo:
    create = SourceTreeInfo()
    create.set_path(path, root_path, setting)
    # create.Children.clear()
    # create.RelationHeaderInfo.clear()
    return create


def _is_ignore(info: SourceTreeInfo, setting: YamlRoot, root_path: str) -> bool:
    if info.get_isdir():
        search_target = setting.exclude_dirs
    elif info.get_isfile():
        if (not info.get_is_head_file()) and (not info.get_is_src_file()):
            return False

        search_target = setting.exclude_files
    else:
        # ファイルでもディレクトリでもない
        return False

    #  ディレクトリの無視設定を反映
    for item in search_target:
        tmp_path = os.path.join(root_path, item)
        if info.get_path() == tmp_path:
            return True

    return False


def _search_sources(path: str, setting: YamlRoot) -> SourceTreeInfo:
    root_info = _create_source_tree_info(path, path, setting)
    parent_info = root_info
    currnet_module_info = parent_info

    is_root = True
    for root, dirs, files in os.walk(path):

        # 親ディレクトリの参照を更新
        if not is_root:
            # dirs の探索時に子要素に格納済みかをチェックする
            # 格納済みの場合は当該オブジェクトを使用する。
            # 未格納の場合は、新規オブジェクトを生成する。
            # (os.walkの探索特性上、本来ありえない想定 -> 下位探索時はすでに上位の探索は完了している。)
            new_info = _create_source_tree_info(root, path, setting)
            check_contains = _is_contains_recursive(new_info, root_info)
            if check_contains[0]:
                parent_info = check_contains[1]
            else:
                parent_info = new_info
        else:
            is_root = False

        if _is_ignore(parent_info, setting, root_info.get_path()):
            continue

        if parent_info.get_module_kind() != ModuleKind.NONE:
            currnet_module_info = parent_info

        for d in dirs:
            # ディレクトリ情報を収集
            new_info_dir = _create_source_tree_info(os.path.join(root, d), path, setting)
            if _is_ignore(new_info_dir, setting, root_info.get_path()):
                continue

            new_info_dir.set_shozoku_module(currnet_module_info)
            parent_info.Children.append(new_info_dir)

        for f in files:
            # ファイル情報を収集
            new_info_file = _create_source_tree_info(os.path.join(root, f), path, setting)
            if _is_ignore(new_info_file, setting, root_info.get_path()):
                continue

            new_info_file.set_shozoku_module(currnet_module_info)
            parent_info.Children.append(new_info_file)

    return root_info


def _output_autogenerate(templete_dir: str, template_file: str, root_tree_info: SourceTreeInfo, setting: YamlRoot):
    # テンプレートファイル(j2)の指定
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templete_dir))
    template = env.get_template(template_file)

    def replace_path_seps(items: []):
        ret = []
        for item in items:
            ret.append(replace_path_sep(item))

        return ret

    def replace_path_sep(base: str):
        tmp = base.replace("\\", "/")
        if tmp[0] == '/':
            tmp = tmp[1:]

        return tmp

    def output_cmakefile(info: SourceTreeInfo, cmakefilepath: str, inc_dir_list: [], module_kind: ModuleKind, source_list: [], lib_list: [], sub_dirs: []):
        # 設定値の指定
        j2data = {
            "title": info.get_name(),
            "cmake_version": setting.compiler.cmake_version,
            "project_name": info.get_name(),
            "clang_iso": setting.compiler.clang_iso,
            "opt_list": setting.compiler.options,
            "inc_dir_list": replace_path_seps(inc_dir_list),
            "module_kind": module_kind,
            "source_list": replace_path_seps(source_list),
            "lib_any": any(lib_list),
            "lib_list": replace_path_seps(lib_list),
            "sub_directories": sub_dirs
        }

        result = template.render(j2data, ModuleKind=ModuleKind)

        with open(cmakefilepath, mode='w', encoding="utf-8") as f:
            f.write(result)

    def output_recursive(inf: SourceTreeInfo):
        if inf != root_tree_info:
            if inf.get_module_kind() == ModuleKind.NONE:
                for child in inf.Children:
                    output_recursive(child)
                return

        # include ディレクトリを収集
        def collect_include_directory(inf_co_dir: SourceTreeInfo) -> []:
            col_ret = []
            for rel in inf_co_dir.RelationHeaderInfo:
                tmp = _cast(SourceTreeInfo, rel)
                dirname = os.path.dirname(tmp.get_path())
                if dirname not in col_ret:
                    col_ret.append(dirname)

            for co_child in inf_co_dir.Children:
                tmp = collect_include_directory(co_child)
                for item in tmp:
                    if item not in col_ret:
                        col_ret.append(item)

            return col_ret

        inc_dir_list = collect_include_directory(inf)

        # ソースファイルのリストを取得
        def collect_source_files(inf_src_dir: SourceTreeInfo) -> []:
            src_ret = []
            if inf_src_dir.get_isfile() and inf_src_dir.get_is_src_file():
                src_filename = inf_src_dir.get_path()
                if src_filename not in src_ret:
                    src_ret.append(src_filename)

            for src_child in inf_src_dir.Children:
                tmp = collect_source_files(src_child)
                for item in tmp:
                    if item not in src_ret:
                        src_ret.append(item)

            return src_ret

        source_list = collect_source_files(inf)

        # lib のリストを取得
        def collect_lib_files(inf_lib_dir: SourceTreeInfo) -> []:
            lib_ret = []
            for lib in inf_lib_dir.RelationHeaderInfo:
                tmp = _cast(SourceTreeInfo, lib)
                tmp_shozoku = _cast(SourceTreeInfo, tmp.get_shozoku_module())
                if inf_lib_dir.get_shozoku_module() != tmp_shozoku:
                    if tmp_shozoku not in lib_ret:
                        lib_ret.append(tmp_shozoku.get_name())

            for lib_child in inf_lib_dir.Children:
                tmp = collect_lib_files(lib_child)
                for item in tmp:
                    if item not in lib_ret:
                        lib_ret.append(item)

            return lib_ret

        lib_list = collect_lib_files(inf)

        filename = os.path.join(inf.get_path(), "CMakeLists.txt")
        if inf == root_tree_info:
            sub_dirs = []
            for child in root_tree_info.Children:
                tmp_child = _cast(SourceTreeInfo, child)
                if tmp_child.get_isdir():
                    sub_dirs.append(tmp_child.get_name())
            output_cmakefile(inf, filename, [], ModuleKind.NONE, [], [], sub_dirs)
        else:
            output_cmakefile(inf, filename, inc_dir_list, inf.get_module_kind(), source_list, lib_list, [])

    output_recursive(root_tree_info)


if __name__ == '__main__':
    execute()
