# coding: utf-8

import os
from logging import root

import yaml
import enum
import copy
import jinja2  # pip install Jinja2
from typing import Tuple
import pathlib


# 生成モジュールの種別
class ModuleKind(enum.Enum):
    # なし(規定値)
    NONE = 0

    # 実行可能
    EXECUTABLE = 1

    # アーカイブ(.a)
    ARCHIVE = 2

    # Shared object(.so)
    SHAREDOBJ = 3


# YAML 設定ファイルクラス start
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

        self._path = str(path).replace("/", os.path.sep)

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


# YAML 設定ファイルクラス end

# ソースファイルのツリー構造管理クラス
class SourceTreeInfo(object):

    # 初期化処理
    def __init__(self):
        self._path = ""                       # フルパス
        self._name = ""                       # ツリー情報を一意に定義する名称
        self._isFile = False                  # ファイルかどうか
        self._isDir = False                   # ディレクトリかどうか
        self.Children = []                    # 子要素(サブディレクトリ or ファイル)
        self.RelationHeaderInfo = []          # 関連するヘッダファイルのツリー情報
        self.RelationLibDirInfo = []          # 関連するライブラリのツリー情報
        self._module_kind = ModuleKind.NONE   # モジュール種別
        self._is_src_file = False             # ソースファイルかどうか
        self._is_head_file = False            # ヘッダファイルかどうｐか
        self._shozoku_module = object         # 所属しているモジュールのツリー情報

    # ツリー情報を設定します。
    # path：フルパス
    # root_path：探索ルートを示すフルパス
    # setting：設定ファイルの情報
    def set_path(self, path: str, root_path: str, setting: YamlRoot):
        self._path = path
        self._name = os.path.join(root_path, path).replace(root_path, "root").replace(os.path.sep, "_")
        self._isDir = os.path.isdir(path)
        self._isFile = os.path.isfile(path)
        for item in setting.module_directories.Item:
            full_path = os.path.join(root_path, item.get_path().replace("/", os.path.sep))
            if full_path == self._path:
                self._module_kind = item.get_kind()
                break

        # ソースファイルかどうかの判定
        for ext in setting.source_file_extensions.extensions:
            if self.get_path().endswith(ext):
                self._is_src_file = True
                break

        # ヘッダファイルかどうかの判定
        for ext in setting.header_file_settings.extensions:
            if self.get_path().endswith(ext):
                self._is_head_file = True
                break

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

    # 所属しているモジュールのツリー情報を設定する
    def set_shozoku_module(self, info: object):
        self._shozoku_module = info
        self._shozoku_module = _cast(SourceTreeInfo, self._shozoku_module)

    def get_shozoku_module(self):
        return self._shozoku_module


# メイン実行処理
def execute():
    filename = "./setting_pic.yml"
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

        if info.get_isfile() and info.get_is_src_file():
            for setting_file_info in setting_file_info_list:
                # ソースファイルからヘッダファイルの情報を収集する
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
                                # ヘッダファイルの探索キーと同一名称のファイルがあれば関連情報に追加する。
                                if is_contains[0]:
                                    if not is_contains[1] in info.RelationHeaderInfo:
                                        info.RelationHeaderInfo.append(is_contains[1])

        for child_item in info.Children:
            search_headerfile(child_item, search_root)

    def set_header_files(info: SourceTreeInfo):
        search_headerfile(info, root_info)

        for child_item in info.Children:
            # print(child_item.get_path())
            set_header_files(child_item)

    set_header_files(root_info)

    def print_tree_info(inf: SourceTreeInfo, depth: int) -> []:
        print_tree_info_ret = []
        indent = ""
        for num in range(0, depth):
            indent = indent + "   "

        print_tree_info_ret.append(f"{ indent }inf-name:{ inf.get_name() }")
        print_tree_info_ret.append(f"{ indent }--- children")
        for child in inf.Children:
            tmp_depth = depth + 1
            tmp_rets = print_tree_info(child, tmp_depth)
            for tmp_ret in tmp_rets:
                print_tree_info_ret.append(tmp_ret)

        print_tree_info_ret.append(f"{ indent }--- Relations")
        for child in inf.RelationHeaderInfo:
            tmp_depth = depth + 1
            tmp_rets = print_tree_info(child, tmp_depth)
            for tmp_ret in tmp_rets:
                print_tree_info_ret.append(tmp_ret)

        return print_tree_info_ret

    tree_print_info = print_tree_info(root_info, 0)
    write_item = ""
    for item in tree_print_info:
        write_item = write_item + "\n" + item

    with open("./tree_info.txt", mode='w', encoding="utf-8") as f:
        f.write(write_item)

    _output_autogenerate(".", "template_cmakefilelist.j2", root_info, setting)


# 同一ファイルがソースツリー内に存在するかどうかを判定
def _is_contains_same_filename_recursive(filename: str, search_base: SourceTreeInfo) -> Tuple[bool, SourceTreeInfo]:
    search_file = os.path.basename(search_base.get_path())
    if filename == search_file:
        return True, search_base

    for child_item in search_base.Children:
        tmp_result = _is_contains_same_filename_recursive(filename, child_item)
        if tmp_result[0]:
            return True, tmp_result[1]

    return False, search_base


# 同一パス(フルパス)がソースツリー内に存在するかどうかを判定
def _is_contains_recursive(info: SourceTreeInfo, search_base: SourceTreeInfo) -> Tuple[bool, SourceTreeInfo]:
    if info.get_path() == search_base.get_path():
        return True, search_base

    for child_item in search_base.Children:
        tmp_result = _is_contains_recursive(info, child_item)
        if tmp_result[0]:
            return True, tmp_result[1]

    return False, info


# ソースツリー管理クラスへのキャスト処理
def _cast(class_type, child_object) -> SourceTreeInfo:
    child_object.__class__ = class_type
    return child_object


# YAML 設定ファイルの読み込み処理
def _load_setting(load_path: str):
    with open(load_path, "r", encoding="utf-8") as file:
        tmp = yaml.safe_load(file)

    #  _cast(YamlRoot, tmp)
    ret = YamlRoot(tmp)
    return ret


# ソースツリーの管理データを生成します
def _create_source_tree_info(path: str, root_path: str, setting: YamlRoot) -> SourceTreeInfo:
    create = SourceTreeInfo()
    create.set_path(path, root_path, setting)
    # create.Children.clear()
    # create.RelationHeaderInfo.clear()
    return create


# 無視対象のファイルかどうかを判定します
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


# ソースファイルをトップダウンに探索し、ツリー管理情報へ変換します。
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

            # for mod in setting.module_directories.Item:
            #     if new_info_dir.get_path() == os.path.join(root_info.get_path(), mod.get_path()):
            #         new_info_dir.set_shozoku_module(currnet_module_info)
            #         parent_info.Children.append(new_info_dir)

        for f in files:
            # ファイル情報を収集
            new_info_file = _create_source_tree_info(os.path.join(root, f), path, setting)
            if _is_ignore(new_info_file, setting, root_info.get_path()):
                continue

            new_info_file.set_shozoku_module(currnet_module_info)
            parent_info.Children.append(new_info_file)

    return root_info


def _get_relation_path(base_path: str, path: str) -> str:
    # base: C:/a/b/c/d/nn.txt
    # path: C:/a/b/e/f/g/kk.txt
    # -> result: ../../../c/d/nn.txt
    tmp_path = path
    if os.path.isdir(tmp_path) or path.endswith(os.path.sep):
        if not tmp_path.endswith(os.path.sep):
            tmp_path = tmp_path + os.path.sep
        if base_path.startswith(tmp_path):
            fixed = base_path.replace(tmp_path, os.path.sep)
            return fixed

    path_tmp_dir = os.path.dirname(tmp_path)
    up_counter = 0
    while True:
        if base_path.startswith(path_tmp_dir):
            # 同一ルートのディレクトリまで上った
            break

        new_path_tmp_dir = os.path.dirname(path_tmp_dir)
        if path_tmp_dir == new_path_tmp_dir:
            # ルートディレクトリまで上った
            break

        path_tmp_dir = new_path_tmp_dir
        up_counter = up_counter + 1

    result = ""
    for index in range(0, up_counter):
        result = result + ".."
        if index != up_counter - 1:
            result = result + os.path.sep

    base_path_remove_dir = base_path.replace(path_tmp_dir, "")
    result = result + base_path_remove_dir
    return result


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
        if len(base) < 2:
            return base
        tmp = base.replace("\\", "/")
        if tmp[0] == '/':
            tmp = tmp[1:]

        return tmp

    def output_cmakefile(info: SourceTreeInfo, cmakefilepath: str, inc_dir_list: [], module_kind: ModuleKind,
                         source_list: [], lib_list: [], sub_dirs: []):
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
        # include ディレクトリを収集
        def collect_include_directory(inf_co_dir: SourceTreeInfo) -> []:
            col_ret = []
            for rel in inf_co_dir.RelationHeaderInfo:
                tmp = _cast(SourceTreeInfo, rel)
                dirname = os.path.dirname(tmp.get_path())
                tmp_shozoku = _cast(SourceTreeInfo, inf_co_dir.get_shozoku_module())
                dirname = _get_relation_path(dirname, tmp_shozoku.get_path())
                if dirname not in col_ret and dirname != "":
                    col_ret.append(dirname)

                inner_rel_ret = collect_include_directory(rel)
                for inner_rel_ret_item in inner_rel_ret:
                    if inner_rel_ret_item not in col_ret and inner_rel_ret != "":
                        col_ret.append(dirname)

            for co_child in inf_co_dir.Children:
                tmp = collect_include_directory(co_child)
                for item in tmp:
                    if item not in col_ret and item != "":
                        col_ret.append(item)

            return col_ret

        # ソースファイルのリストを取得
        def collect_source_files(inf_src_dir: SourceTreeInfo) -> []:
            src_ret = []
            if inf_src_dir.get_isfile() and inf_src_dir.get_is_src_file():
                src_filename = inf_src_dir.get_path()
                tmp_shozoku = _cast(SourceTreeInfo, inf_src_dir.get_shozoku_module())
                src_filename = _get_relation_path(src_filename, tmp_shozoku.get_path())
                if src_filename not in src_ret:
                    src_ret.append(src_filename)

            for src_child in inf_src_dir.Children:
                tmp = collect_source_files(src_child)
                for item in tmp:
                    if item not in src_ret and item != "":
                        src_ret.append(item)

            return src_ret

        # lib のリストを取得
        def collect_lib_files(inf_lib_dir: SourceTreeInfo) -> []:
            lib_ret = []
            for lib in inf_lib_dir.RelationHeaderInfo:
                tmp = _cast(SourceTreeInfo, lib)
                tmp_shozoku = _cast(SourceTreeInfo, tmp.get_shozoku_module())
                if inf_lib_dir.get_shozoku_module() != tmp_shozoku:
                    if tmp_shozoku not in lib_ret:
                        if tmp_shozoku.get_shozoku_module() == ModuleKind.SHAREDOBJ \
                                or tmp_shozoku.get_shozoku_module() == ModuleKind.ARCHIVE:
                            lib_ret.append(tmp_shozoku.get_name())

                inner_lib_ret = collect_lib_files(lib)
                for inner_lib_ret_item in inner_lib_ret:
                    if inner_lib_ret_item not in lib_ret and inner_lib_ret != "":
                        lib_ret.append(inner_lib_ret_item)

            for lib_child in inf_lib_dir.Children:
                tmp = collect_lib_files(lib_child)
                for item in tmp:
                    if item not in lib_ret:
                        lib_ret.append(item)

            return lib_ret

        if inf == root_tree_info or inf.get_module_kind() != ModuleKind.NONE:
            filename = os.path.join(inf.get_path(), "CMakeLists.txt")
            if inf == root_tree_info:
                sub_dirs = []
                for child in setting.module_directories.Item:
                    sub_dirs.append(child.get_path().replace(os.path.sep, "/"))
                output_cmakefile(inf, filename, [], ModuleKind.NONE, [], [], sub_dirs)
            else:
                inc_dir_list = collect_include_directory(inf)
                source_list = collect_source_files(inf)
                lib_list = collect_lib_files(inf)
                output_cmakefile(inf, filename, inc_dir_list, inf.get_module_kind(), source_list, lib_list, [])

        for child in inf.Children:
            output_recursive(child)

    output_recursive(root_tree_info)


if __name__ == '__main__':
    execute()
