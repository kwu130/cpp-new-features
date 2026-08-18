# C++14：让 C++11 更容易使用

C++14 是一次以完善为主的标准更新。它没有改变 C++11 的现代化方向，而是减少样板代码、放宽过于严格的编译期限制，并补齐智能指针工厂、索引序列和共享锁等实用设施。

本专题假设读者已经掌握 C++11 的 `auto`、Lambda、移动语义、`constexpr`、智能指针和基础并发。文章继续采用“旧版本限制 → 最小语法 → 完整示例 → 底层模型 → 工程边界”的渐进结构。

## 如何阅读

第一次阅读先关注每篇前半部分：理解 C++11 中哪里写得繁琐，以及 C++14 新写法如何改善。第二次阅读再进入返回引用、模板实例化、变量模板实体身份、数组工厂和锁公平性等进阶问题。

所有 `cpp` 示例都以 `-std=c++14 -Wall -Wextra -pedantic` 编译运行。文档不会使用 C++17 才出现的结构化绑定、折叠表达式、内联变量或 `if constexpr`。

## 推荐学习路线

### 第一阶段：日常语言表达

1. [泛型 Lambda 与初始化捕获](lambdas.md)
2. [返回类型推导与 `decltype(auto)`](return-type-deduction.md)
3. [变量模板与放宽的 `constexpr`](compile-time.md)
4. [二进制字面量与数字分隔符](literals.md)

这一阶段重点理解：泛型 Lambda 仍是模板、`auto` 与 `decltype(auto)` 的返回语义不同、C++14 常量函数为何能使用循环，以及数字写法不会改变整数类型规则。

### 第二阶段：标准库补全

5. [`make_unique`](make-unique.md)
6. [`integer_sequence`](integer-sequence.md)
7. [`shared_timed_mutex`、`exchange` 与常用库增强](library-enhancements.md)

这一阶段重点理解：独占所有权工厂有哪些重载、索引怎样从类型包进入表达式，以及共享读锁和普通状态替换分别解决什么问题。

## 特性覆盖矩阵

| 领域 | C++14 主要改进 | 对应专题 |
| --- | --- | --- |
| Lambda | `auto` 参数、初始化捕获、移动捕获 | [泛型 Lambda](lambdas.md) |
| 函数返回 | 普通函数 `auto` 返回、`decltype(auto)` | [返回类型推导](return-type-deduction.md) |
| 编译期 | 放宽的 `constexpr`、变量模板 | [编译期增强](compile-time.md) |
| 字面量 | `0b` 二进制写法、单引号数字分隔符 | [字面量](literals.md) |
| 所有权 | 单对象和未知界数组的 `make_unique` | [`make_unique`](make-unique.md) |
| 泛型适配 | `integer_sequence`、`index_sequence` | [整数序列](integer-sequence.md) |
| 并发库 | `shared_timed_mutex`、`shared_lock` | [库增强](library-enhancements.md) |
| 通用工具 | `exchange`、透明比较器、异构查找、`quoted` | [库增强](library-enhancements.md) |

## 容易混淆的版本边界

- 泛型 Lambda 的 `auto` 参数属于 C++14，但显式模板参数列表要到 C++20；
- `decltype(auto)` 属于 C++14，不能用于 C++11；
- C++14 放宽 `constexpr` 函数体，但大量标准容器尚不能参与常量求值；
- `make_unique` 属于 C++14，`make_unique_for_overwrite` 要到 C++20；
- `integer_sequence` 属于 C++14，折叠表达式属于 C++17；
- `shared_timed_mutex` 属于 C++14，非定时的 `shared_mutex` 属于 C++17；
- `random_shuffle` 在 C++14 被弃用、C++17 移除，应迁移到接收显式引擎的 `shuffle`；
- `[[deprecated]]` 属性属于 C++14，而 `[[nodiscard]]`、`[[fallthrough]]` 和 `[[maybe_unused]]` 属于 C++17。

## 学习完成标准

完成本专题后，应能把一段 C++11 代码升级到 C++14，同时解释每项改动是否影响对象所有权、返回值类别、模板实例数量、常量求值或线程同步，而不是只会替换语法。

[返回仓库总览](../../README.md)
