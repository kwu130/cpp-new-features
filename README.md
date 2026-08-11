# C++11–C++20 新特性指南

这是一个面向已有 C++98/03 基础开发者的现代 C++ 中文文档库，聚焦实际开发中高频或具有重要设计意义的语言与标准库特性。

## 阅读路线

建议按 C++11、C++14、C++17、C++20 的顺序阅读。每篇文章都按“问题背景 → 语义规则 → 底层模型 → 完整示例 → 工程实践”的路径展开，并包含可复制运行的程序。

第一次阅读时先掌握“为什么需要”和主示例；第二次阅读再进入底层机制、边界条件与性能权衡。模板、并发、协程和 Modules 等主题依赖较多，建议先完成同版本的基础语言章节。

| 标准 | 状态 | 入口 |
| --- | --- | --- |
| C++11 | 已完成 | [进入专题](docs/cpp11/README.md) |
| C++14 | 已完成 | [进入专题](docs/cpp14/README.md) |
| C++17 | 已完成 | [进入专题](docs/cpp17/README.md) |
| C++20 | 已完成 | [进入专题](docs/cpp20/README.md) |

## 示例保证

仓库中的每个 C++ 代码围栏都会由 `tools/verify_examples.py` 提取、编译并运行。普通示例同时接受 GCC 和 Clang 验证，GitHub Actions 会在每次推送和 Pull Request 时执行全量检查。

验证器还会检查所有相对链接。教程篇幅只允许通过特性专属的语义、接口、实现原理、示例和工程经验扩充，不使用重复附录或通用模板填充。

## 特性速查

- C++11：[类型推导](docs/cpp11/type-deduction.md)、[移动语义](docs/cpp11/move-semantics.md)、[Lambda](docs/cpp11/lambdas.md)、[智能指针](docs/cpp11/smart-pointers.md)、[并发](docs/cpp11/concurrency.md)
- C++14：[泛型 Lambda](docs/cpp14/lambdas.md)、[`decltype(auto)`](docs/cpp14/return-type-deduction.md)、[`constexpr`](docs/cpp14/compile-time.md)、[`make_unique`](docs/cpp14/make-unique.md)
- C++17：[结构化绑定与 `if constexpr`](docs/cpp17/control-flow.md)、[词汇类型](docs/cpp17/vocabulary-types.md)、[`string_view`](docs/cpp17/string-view.md)、[Filesystem](docs/cpp17/filesystem.md)、[`pmr`](docs/cpp17/pmr.md)
- C++20：[Concepts](docs/cpp20/concepts.md)、[Ranges](docs/cpp20/ranges.md)、[Coroutines](docs/cpp20/coroutines.md)、[Modules](docs/cpp20/modules.md)、[`jthread`](docs/cpp20/jthread.md)

下面的最小程序同时用于验证文档示例链路：

<!-- example id="repository-smoke-test" std="c++11" file="main.cpp" kind="single" compilers="all" output="documentation ready" -->
```cpp
#include <iostream>

int main() {
    std::cout << "documentation ready\n";
}
```

## 授权

文档采用 [CC BY 4.0](LICENSE.md) 许可。参与贡献前请阅读 [贡献指南](CONTRIBUTING.md)。

规范语义和版本归属以 [权威资料与引用规范](docs/official-sources.md) 中列出的 WG21 工作草案与提案为准。
