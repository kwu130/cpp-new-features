# C++14：完善 C++11

C++14 以易用性改进为主：Lambda 更通用，编译期计算限制更少，并补齐了一批标准库工具。

## 推荐学习顺序

先学习泛型 Lambda、返回类型推导和放宽的 `constexpr`，它们直接延续 C++11 核心语言；再学习 `make_unique` 和字面量等日常工具；最后进入索引序列与共享互斥量等偏泛型/并发主题。

- [泛型 Lambda 与初始化捕获](lambdas.md)
- [返回类型推导与 `decltype(auto)`](return-type-deduction.md)
- [变量模板与放宽的 `constexpr`](compile-time.md)
- [二进制字面量与数字分隔符](literals.md)
- [`make_unique`](make-unique.md)
- [`integer_sequence`](integer-sequence.md)
- [`shared_timed_mutex` 与 `exchange`](library-enhancements.md)

[返回总览](../../README.md)
