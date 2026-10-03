# C++23：日常接口完善与范围扩展

C++23 延续 C++20 的语言与库模型：新增局部语法、结果与回调类型，完善 Ranges，提供多维视图、同步生成器及诊断工具。本入口覆盖常用且具有设计意义的能力，不是标准全部变更的逐条清单。

面向掌握基本 C++ 的读者。建议按 C++11 → C++14 → C++17 → C++20 → C++23 阅读；各篇给出具体前置链接，不要求先读完之前版本所有高级专题。需要时先补齐[基础知识](../prerequisites.md)。

## 推荐学习路线

### 第一阶段：局部语法与日常工具

1. [auto(x)、整数后缀、多参数下标与静态调用](language-improvements.md)
2. [if consteval 与 constexpr 增强](compile-time.md)
3. [枚举、字节交换、转发与不可达分支](utility-and-bit.md)
4. [字符串与容器增强](strings-and-containers.md)
5. [print 与 println](print.md)

先学可以局部采用的改进；forward_like 和 unreachable 可在理解引用与前置条件后回读。

### 第二阶段：结果、可选流程与回调所有权

6. [expected：结果或错误](expected.md)
7. [optional 的串联操作](optional-monadic.md)
8. [move_only_function](move-only-function.md)
9. [显式对象参数](explicit-object-parameter.md)

先分清“无值”与“错误原因”，再考虑流水线写法。显式对象参数用于消除重复重载，不会自动解决返回引用的生命周期问题。

### 第三阶段：范围、存储与高级工具

10. [Ranges：to、zip、enumerate 与 chunk](ranges.md)
11. [mdspan：多维借用视图](mdspan.md)
12. [flat_map 与 flat_set](flat-containers.md)
13. [generator：同步协程序列](generator.md)
14. [stacktrace：诊断快照](stacktrace.md)

先辨认谁拥有数据，再分析失效、单次遍历和工具链支持。generator 需要 C++20 协程背景，stacktrace 需要结合目标符号与运行环境核对诊断质量。

## 特性与接口归属

| 领域 | 本版介绍 | 重要边界 |
| --- | --- | --- |
| 语言 | 显式对象参数、if consteval、auto(x)、z/uz、多参数下标、static operator() | 不把后续标准能力写作 C++23 初版能力 |
| 结果 | expected、optional/expected 串联操作 | optional 类型本身属于 C++17 |
| 回调 | move_only_function | 不包括 C++26 function_ref/copyable_function |
| 输出 | print、println | format 类型与格式基础属于 C++20 |
| 范围 | ranges::to、zip、enumerate、chunk 等 | owning_view 等属于 C++20 回溯缺陷修正 |
| 存储 | mdspan、flat_map/flat_set 与 multi 版本 | mdspan 借用数据，扁平容器拥有元素 |
| 协程 | generator | 同步、惰性、单次遍历，不是异步 task |
| 诊断 | stacktrace | 内容依赖实现、符号及优化，允许空快照 |

## 运行本版示例

所有源码内嵌在对应专题的 `cpp example` 围栏中，按 `-std=c++23 -Wall -Wextra -pedantic` 编译，运行并核对输出。无需维护另一份源码目录。

```shell
python3 tools/verify_examples.py --list --path docs/cpp23
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23
python3 tools/verify_examples.py --compiler g++ --path docs/cpp23
```

版本名与标准库实现支持是两个问题。`-std=c++23` 不会升级标准库；用 `--version` 确认实际编译器，macOS 的 g++ 可能仍是 Apple Clang。普通示例面向 GCC 和 Clang，不按编译器品牌推断某个库接口是否可用。

工具链支持尚不普遍的示例携带 `requires="__cpp_lib_expected>=202202"` 这类元数据。验证器在相同标准模式下包含 `<version>` 检查特性宏；能力缺失时显示 `SKIP` 与要求，支持后仍正常编译链接、运行及检查输出。能力探测报错、示例编译失败或输出不匹配都会失败，不会被伪装成“不支持”。缺少宏时也不会改编成旧接口来取得通过。

现有 Ubuntu CI 的 GCC/Clang 矩阵会自动提取本版示例。CI 的跳过项仍须阅读；两个编译器都跳过不表示该示例经过实际验证。

## 本次本机验证快照

本版新增 14 篇专题、27 组示例，采用本机 Apple Clang 21 与自带标准库验证：**22 组通过、5 组跳过**。下列示例缺少所要求的特性宏，没有实际编译运行：

| 示例 | 所需支持声明 |
| --- | --- |
| cpp23-generator | `__cpp_lib_generator>=202207` |
| cpp23-move-only-function | `__cpp_lib_move_only_function>=202110` |
| cpp23-ranges-enumerate | `__cpp_lib_ranges_enumerate>=202302` |
| cpp23-ranges-chunk | `__cpp_lib_ranges_chunk>=202202` |
| cpp23-stacktrace | `__cpp_lib_stacktrace>=202011` |

全仓库现有 166 组示例，实际为 **159 组通过、7 组跳过**；另两组是原有的 GCC 专用并行算法与 Modules。本机 g++ 仍为 Apple Clang，未完成真正的 GCC 验证，也未触发远程 CI。

另外验证了 7 个能力检查与失败边界：支持时正常通过、缺少能力时明确跳过、非法要求拒绝、同组要求不一致拒绝、能力探测错误报错、支持后的编译错误报错、输出不符报错。Markdown 围栏、相对链接与章节锚点、示例元数据与 ID 保留检查以及 `git diff --check` 均通过。此快照不代表其他工具链的支持程度；换环境后重新执行上面的命令。

## 学习完成标准

能说明一项改进的旧写法与新写法，指出成功/失败状态、对象所有权和引用失效条件，并区分标准归属、特性宏声明与真正的编译运行结果。新接口不意味着应一次替换全部旧代码；依据业务约束逐项采用。

规范以 [C++23 草案 N4950](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2023/n4950.pdf) 与对应提案核对；当前工作草案还包含后续版本，引用方法见[权威资料](../official-sources.md)。实现查询使用 [Clang](https://clang.llvm.org/cxx_status)、[libc++](https://libcxx.llvm.org/Status/Cxx23.html) 与 [libstdc++](https://gcc.gnu.org/onlinedocs/libstdc++/manual/status.html) 官方资料，最终以目标环境实测为准。

[返回 C++20](../cpp20/README.md) · [返回仓库总览](../../README.md)
