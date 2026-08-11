# C++11–C++20 新特性指南

这是一个面向已有 C++98/03 基础开发者的现代 C++ 中文文档库，聚焦实际开发中高频或具有重要设计意义的语言与标准库特性。

## 阅读路线

建议按 C++11、C++14、C++17、C++20 的顺序阅读。每篇文章都包含可复制运行的完整示例、适用场景和常见陷阱。

| 标准 | 状态 | 入口 |
| --- | --- | --- |
| C++11 | 已完成 | [进入专题](docs/cpp11/README.md) |
| C++14 | 计划中 | 完成后开放 |
| C++17 | 计划中 | 完成后开放 |
| C++20 | 计划中 | 完成后开放 |

## 示例保证

仓库中的每个 C++ 代码围栏都会由 `tools/verify_examples.py` 提取、编译并运行。普通示例同时接受 GCC 和 Clang 验证，GitHub Actions 会在每次推送和 Pull Request 时执行全量检查。

## 特性速查

- C++11：[类型推导](docs/cpp11/type-deduction.md)、[移动语义](docs/cpp11/move-semantics.md)、[Lambda](docs/cpp11/lambdas.md)、[智能指针](docs/cpp11/smart-pointers.md)、[并发](docs/cpp11/concurrency.md)

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
