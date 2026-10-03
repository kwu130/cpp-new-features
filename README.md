# C++11–C++23 新特性指南

这是一个面向已有 C++98/03 基础开发者的现代 C++ 中文文档库，聚焦实际开发中高频或具有重要设计意义的语言与标准库特性。

## 阅读路线

建议先补齐[基础知识](docs/prerequisites.md)，再按 C++11、C++14、C++17、C++20、C++23 的顺序阅读。主要专题按“问题 → 传统写法 → 最小示例 → 解释与场景 → 注意事项 → 深入原理”展开，简单特性会合并部分环节。

第一次阅读时先掌握“为什么需要”和最小示例，确认自己能解释输出和适用场景；第二次再进入底层机制与性能权衡。各版本入口给出递进顺序，各专题开头链接需要的前置知识。移动语义先学资源转移，学完参数包后再返回完美转发；Concepts 先于模板 Lambda 的约束和 Ranges，协程在生命周期与资源管理之后学习。

| 标准 | 状态 | 入口 |
| --- | --- | --- |
| C++11 | 已完成 | [进入专题](docs/cpp11/README.md) |
| C++14 | 已完成 | [进入专题](docs/cpp14/README.md) |
| C++17 | 已完成 | [进入专题](docs/cpp17/README.md) |
| C++20 | 已完成 | [进入专题](docs/cpp20/README.md) |
| C++23 | 已覆盖常用专题，部分接口依赖工具链支持 | [进入专题](docs/cpp23/README.md) |

## 从正在遇到的问题进入

主路线仍按标准版本递进；如果已有具体问题，也可以从这里开始。进入专题后先看前置链接、最小程序及输出，再读组合练习和深入规则。

| 我想解决的问题 | 建议先读 |
| --- | --- |
| 分不清复制、引用和资源转交 | [类型推导](docs/cpp11/type-deduction.md)、[复制与移动](docs/cpp11/move-semantics.md#先比较复制与移动) |
| 不想在每条退出路径手动 delete | [智能指针](docs/cpp11/smart-pointers.md) |
| 想把一小段操作交给算法或回调 | [Lambda](docs/cpp11/lambdas.md) |
| 函数可能没有结果，或者需要返回失败原因 | [optional](docs/cpp17/vocabulary-types.md)、[expected](docs/cpp23/expected.md) |
| 看不懂参数包、索引展开和折叠 | [参数包](docs/cpp11/templates.md)、[整数序列](docs/cpp14/integer-sequence.md)、[折叠表达式](docs/cpp17/fold-expressions.md) |
| 想让模板只接受合适的类型 | [Concepts](docs/cpp20/concepts.md) |
| 想过滤、转换一组数据 | [Ranges](docs/cpp20/ranges.md) |
| 想等后台任务完成，或避免共享数据被同时修改 | [线程、锁与结果](docs/cpp11/concurrency.md)、[jthread](docs/cpp20/jthread.md) |
| 想理解函数怎样暂停后继续 | [协程的手动暂停与恢复](docs/cpp20/coroutines.md#先看暂停与恢复) |

## 示例保证

仓库中的每个 C++ 代码围栏都会由 `tools/verify_examples.py` 提取。普通示例同时面向 GCC 和 Clang 编译运行，GitHub Actions 会在每次推送和 Pull Request 时执行全量检查。C++23 中支持不普遍的示例按特性测试宏检查能力，缺少能力会明确跳过；支持后的编译、链接、运行或输出错误仍会导致验证失败。

验证器还会检查相对链接的目标文件是否存在。

示例源码保存在文档内，围栏的 `id` 用于识别程序，Modules 的多个围栏组成同一个程序。可以复制完整示例自行编译，也可以从仓库根目录只运行某个专题：

```shell
python3 tools/verify_examples.py --list
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp11/move-semantics.md
python3 tools/verify_examples.py --compiler clang++
python3 tools/verify_examples.py --compiler g++
```

`--path` 同样接受版本目录。验证器使用各示例指定的 C++ 标准，核对退出状态和声明的输出。GCC 专用的并行算法与 Modules 示例会在 Clang 下跳过；macOS 上名为 `g++` 的命令也可能是 Apple Clang，运行前用 `--version` 确认，不能把两次 Clang 验证当作双编译器验证。

## 特性速查

- C++11：[类型推导](docs/cpp11/type-deduction.md)、[移动语义](docs/cpp11/move-semantics.md)、[Lambda](docs/cpp11/lambdas.md)、[智能指针](docs/cpp11/smart-pointers.md)、[并发](docs/cpp11/concurrency.md)
- C++14：[泛型 Lambda](docs/cpp14/lambdas.md)、[`decltype(auto)`](docs/cpp14/return-type-deduction.md)、[`constexpr`](docs/cpp14/compile-time.md)、[`make_unique`](docs/cpp14/make-unique.md)
- C++17：[结构化绑定与 `if constexpr`](docs/cpp17/control-flow.md)、[词汇类型](docs/cpp17/vocabulary-types.md)、[`string_view`](docs/cpp17/string-view.md)、[Filesystem](docs/cpp17/filesystem.md)、[`pmr`](docs/cpp17/pmr.md)
- C++20：[Concepts](docs/cpp20/concepts.md)、[Ranges](docs/cpp20/ranges.md)、[Coroutines](docs/cpp20/coroutines.md)、[Modules](docs/cpp20/modules.md)、[`jthread`](docs/cpp20/jthread.md)
- C++23：[显式对象参数](docs/cpp23/explicit-object-parameter.md)、[`expected`](docs/cpp23/expected.md)、[Ranges 扩展](docs/cpp23/ranges.md)、[`print`](docs/cpp23/print.md)、[`mdspan`](docs/cpp23/mdspan.md)、[`generator`](docs/cpp23/generator.md)

下面的最小程序同时用于验证文档示例链路：

```cpp example id="repository-smoke-test" std="c++11" file="main.cpp" kind="single" compilers="all" output="documentation ready"
#include <iostream>

int main() {
    std::cout << "documentation ready\n";
}
```

## 授权

文档采用 [CC BY 4.0](LICENSE.md) 许可。参与贡献前请阅读 [贡献指南](CONTRIBUTING.md)。

规范语义和版本归属以 [权威资料与引用规范](docs/official-sources.md) 中列出的 WG21 工作草案与提案为准。
