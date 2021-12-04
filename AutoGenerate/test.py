# coding: utf-8

import os
import yaml
import enum
import jinja2  # pip install Jinja2


class ModuleKind(enum.Enum):
    EXECUTABLE = 1
    ARCHIVE = 2
    SHAREDOBJ = 3


class SourceTreeInfo:

    def __init__(self):
        self._path = ""
        self._name = ""
        self._isFile = False
        self._isDir = False
        self.Children = []
        self.RelationTreeInfo = []

    def set_path(self, path: str):
        self._path = path
        self._name = os.path.basename(path)
        self._isDir = os.path.isdir(path)
        self._isFile = os.path.isfile(path)

    def get_path(self):
        return self._path

    def get_isdir(self):
        return self._isDir

    def get_isfile(self):
        return self._isFile


def execute():
    filename = "./setting.yml"
    setting = _load_setting(filename)

    input_dir = input('探索対象のディレクトリを指定: ')
    root_info = _search_sources(input_dir)

    def print_recursive(info: SourceTreeInfo):
        for child_item in info.Children:
            print(child_item.get_path())
            print_recursive(child_item)

    print_recursive(root_info)

    # ディレクトリ構造から収集したいもの
    # title：全体を識別する名称
    # - ルートフォルダの名称
    # project_name：各モジュール名称
    # - 各モジュールフォルダの名称。
    # inc_dir_list：関連するヘッダのインクルードパス
    # - ソースファイルがincludeしているヘッダファイルのありか
    # source_list ：当該モジュールフォルダ内のソースファイル
    # - 各モジュールフォルダ配下のソースファイル
    # isLinkLibs/lib_list：ライブラリ(.a/soリンク)
    # - 各モジュールフォルダ内で他のモジュールフォルダを参照している場合


def is_contains_recursive(info: SourceTreeInfo, search_base: SourceTreeInfo) -> tuple[bool, SourceTreeInfo]:

    if info.get_path() == search_base.get_path():
        return True, search_base

    for child_item in info.Children:
        tmp_result = is_contains_recursive(info, child_item)
        if tmp_result[0]:
            return True, tmp_result[1]

    return False, info


def cast(class_type, child_object):
    child_object.__class__ = class_type
    return child_object


def _load_setting(load_path: str):
    with open(load_path, "r", encoding="utf-8") as file:
        tmp = yaml.safe_load(file)

    return tmp


def _create_source_tree_info(path: str) -> SourceTreeInfo:
    create = SourceTreeInfo()
    create.set_path(path)
    create.Children.clear()
    create.RelationTreeInfo.clear()
    cast(SourceTreeInfo, create)
    return create


def _search_sources(path: str) -> SourceTreeInfo:

    root_info = _create_source_tree_info(path)
    parent_info = root_info

    is_root = True
    for root, dirs, files in os.walk(path):
        # 親ディレクトリの参照を更新
        if not is_root:
            new_info = _create_source_tree_info(root)
            check_contains = is_contains_recursive(new_info, root_info)
            if check_contains[0]:
                parent_info = check_contains[1]
            else:
                parent_info = new_info
        else:
            is_root = False

        for d in dirs:
            # ディレクトリ情報を収集
            new_info_dir = _create_source_tree_info(os.path.join(root, d))
            parent_info.Children.append(new_info_dir)

        for f in files:
            # ファイル情報を収集
            new_info_file = _create_source_tree_info(os.path.join(root, f))
            parent_info.Children.append(new_info_file)

    return root_info


def _output_autogenerate(templete_dir: str, template_file: str, root_tree_info: SourceTreeInfo):
    # テンプレートファイル(j2)の指定
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templete_dir))
    template = env.get_template(template_file)

    # 設定値の指定
    # j2data = {
    #     "title": "テストcmakefile",
    #     "cmake_version": setting["CMakefileList"]["compiler"]["cmake_version"],
    #     "project_name": "テストプロジェクト",
    #     "clang_iso": setting["CMakefileList"]["compiler"]["clang_iso"],
    #     "opt_list": setting["CMakefileList"]["compiler"]["options"],
    #     "inc_dir_list": ["inc1", "inc2", "inc3"],
    #     "module_kind": ModuleKind.EXECUTABLE,
    #     "source_list":  ["src1.c", "src2.c", "src3.c"],
    #     "isLinkLibs": True,
    #     "lib_list": ["lib1", "lib2", "lib3"]
    # }
    #
    # result = template.render(j2data, ModuleKind=ModuleKind)
    # cmakefile_path = "./cmakefile.txt"
    #
    # with open(cmakefile_path, mode='w', encoding="utf-8") as f:
    #     f.write(result)


if __name__ == '__main__':
    execute()

