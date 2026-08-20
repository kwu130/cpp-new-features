# C++17：表达力、对象模型与实用标准库

C++17 是一次覆盖面很广的标准更新。它一方面让泛型与日常控制流更容易阅读，另一方面通过纯右值模型、内联变量等变化修正对象与链接语义，还把文件系统、字符串视图、词汇类型和多态内存资源等长期工程需求纳入标准库。

本专题假设读者已掌握 C++11/14 的类型推导、移动语义、Lambda、可变参数模板、智能指针和基础并发。文章采用“旧版本问题 → 最小语法 → 完整示例 → 语义模型 → 工程边界”的渐进结构；第一次阅读可先掌握每篇前半部分，再进入 ODR、实例化、生命周期、并发和分配器细节。

## 如何使用本专题

所有标记为 `cpp` 的示例都由仓库验证器提取，并以 `-std=c++17 -Wall -Wextra -pedantic` 编译运行。普通示例同时面向 GCC 与 Clang；并行算法示例受本地标准库实现影响，在专门的 GCC CI 任务中验证。

学习时不要只记新名字。C++17 中最容易出错的地方往往是边界：结构化绑定是否复制、纯右值与 NRVO 是否属于同一保证、视图是否悬空、并行回调是否允许重排，以及 PMR 资源是否比容器活得更久。

## 推荐学习路线

### 第一阶段：日常表达与泛型代码

1. [结构化绑定与条件语句增强](control-flow.md)
2. [折叠表达式](fold-expressions.md)
3. [类模板实参推导](ctad.md)
4. [模板参数与属性](templates-and-attributes.md)

这一阶段先解决“代码怎样写得更直接”：拆解复合对象、缩短查询变量作用域、按类型丢弃模板分支、归约参数包、从构造实参推导类模板参数，并用标准属性表达诊断意图。

### 第二阶段：对象与程序实体

5. [保证的复制消除](copy-elision.md)
6. [内联变量与嵌套命名空间](inline-variables.md)

这两篇不只是语法简化。复制消除专题涉及 C++17 纯右值和临时量实质化模型；内联变量专题涉及跨翻译单元的单一定义规则、实体地址与动态初始化。

### 第三阶段：高频词汇与系统接口

7. [`string_view`](string-view.md)
8. [`optional`、`variant` 与 `any`](vocabulary-types.md)
9. [Filesystem](filesystem.md)
10. [`from_chars` 与 `to_chars`](charconv.md)

这一阶段的共同主题是“接口契约”：谁拥有数据、缺失或多态状态怎样表示、路径操作是否访问外部世界、解析成功是否意味着消费了完整输入。

### 第四阶段：泛型库、容器与并发

11. [`apply` 与 `invoke`](invoke-apply.md)
12. [容器接口增强](containers.md)
13. [`scoped_lock` 与 `shared_mutex`](concurrency.md)
14. [带执行策略的算法](parallel-algorithms.md)
15. [多态内存资源 `pmr`](pmr.md)

这些设施适合在理解基础对象生命周期和内存模型后学习。它们减少样板代码，但不会替调用方证明可调用性、节点所有权、死锁自由、数据竞争自由或资源生命周期。

## 特性覆盖矩阵

| 领域 | C++17 主要能力 | 对应专题 |
| --- | --- | --- |
| 控制流 | 结构化绑定、选择语句初始化、`if constexpr` | [控制流增强](control-flow.md) |
| 参数包 | 一元/二元、左/右折叠表达式 | [折叠表达式](fold-expressions.md) |
| 模板推导 | 隐式指引、自定义指引、复制推导候选 | [CTAD](ctad.md) |
| 模板值与诊断 | `auto` 非类型模板参数、三项标准属性 | [模板参数与属性](templates-and-attributes.md) |
| 对象模型 | 延迟实质化、保证场景、NRVO 边界 | [保证的复制消除](copy-elision.md) |
| ODR 与声明 | 内联变量、内联静态成员、嵌套命名空间 | [内联变量](inline-variables.md) |
| 只读文本 | 非拥有字符视图、切片、搜索 | [`string_view`](string-view.md) |
| 状态建模 | `optional`、`variant`、`any` | [词汇类型](vocabulary-types.md) |
| 文件系统 | `path`、状态查询、遍历与文件操作 | [Filesystem](filesystem.md) |
| 字符转换 | 无区域设置、无异常的低层数值转换 | [Charconv](charconv.md) |
| 调用适配 | 统一调用协议、tuple-like 实参展开 | [`invoke` 与 `apply`](invoke-apply.md) |
| 关联容器 | 节点句柄、`merge`、插入与覆盖接口 | [容器增强](containers.md) |
| 锁 | 多互斥量 RAII、共享读写互斥量 | [并发增强](concurrency.md) |
| 算法 | 执行策略、归约与扫描 | [并行算法](parallel-algorithms.md) |
| 内存分配 | `memory_resource`、PMR 容器与资源策略 | [多态内存资源](pmr.md) |

## 容易混淆的版本边界

- 泛型 Lambda 属于 C++14；Lambda 显式模板参数列表要到 C++20；
- `if constexpr` 属于 C++17，C++20 的 Concepts 才能在声明层直接表达大量模板约束；
- CTAD 属于 C++17，聚合类型的推导候选规则在后续标准继续扩展；
- `[[deprecated]]` 属于 C++14，`[[nodiscard]]`、`[[maybe_unused]]` 与 `[[fallthrough]]` 属于 C++17；
- C++17 保证若干同类型纯右值场景，但具名返回值优化 NRVO 仍不是强制保证；
- `string_view` 不拥有字符，C++20 才为字符串和视图补充 `starts_with`、`ends_with`；
- `optional`、`variant` 与 `any` 属于 C++17；`expected` 不属于 C++17；
- `shared_timed_mutex` 属于 C++14，非定时的 `shared_mutex` 与 `scoped_lock` 属于 C++17；
- 执行策略属于 C++17，但不同标准库的实现完整度和运行时后端可能不同；
- `contains` 要到 C++20，C++17 关联容器应使用 `find` 或 `count`；
- `std::format`、Ranges、Coroutines、`span` 与 Modules 都属于 C++20，不应出现在 C++17 示例中。

## 学习完成标准

完成本专题后，应能把 C++14 代码升级到 C++17，并为每项改动回答四个问题：它只减少语法还是改变对象模型；它是否创建或拥有对象；失败与异常怎样传播；跨翻译单元、线程或资源边界时还需满足什么条件。

[返回仓库总览](../../README.md)
