# C++17：表达力与标准库扩展

C++17 明显提升了泛型代码的可读性，并加入文件系统、词汇类型、字符串视图等实用设施。

## 推荐学习顺序

1. 表达力：结构化绑定、`if constexpr`、折叠表达式、CTAD。
2. 对象与类型：复制消除、内联变量、属性与词汇类型。
3. 高频库：`string_view`、Filesystem、字符转换和容器增强。
4. 进阶设施：调用适配、并行算法、共享锁和 PMR。

词汇类型和 `string_view` 需要重点审查对象布局与生命周期；并行算法和 PMR 建议在理解基础内存模型后学习。

- [结构化绑定与条件语句增强](control-flow.md)
- [折叠表达式](fold-expressions.md)
- [内联变量与嵌套命名空间](inline-variables.md)
- [类模板实参推导](ctad.md)
- [保证的复制消除](copy-elision.md)
- [模板参数与属性](templates-and-attributes.md)
- [`string_view`](string-view.md)
- [`optional`、`variant` 与 `any`](vocabulary-types.md)
- [Filesystem](filesystem.md)
- [`from_chars` 与 `to_chars`](charconv.md)
- [`apply` 与 `invoke`](invoke-apply.md)
- [带执行策略的算法](parallel-algorithms.md)
- [`scoped_lock` 与 `shared_mutex`](concurrency.md)
- [容器接口增强](containers.md)
- [多态内存资源 `pmr`](pmr.md)

[返回总览](../../README.md)
