# 权威资料与引用规范

本仓库以 WG21 标准工作草案和 WG21 提案为技术事实来源。普通教程、博客和问答网站可以帮助理解，但不用于决定规范语义。

## 如何阅读资料

1. 先阅读特性提案，理解它试图解决的问题、设计取舍和最初加入标准时的接口。
2. 再阅读当前工作草案对应章节，核对约束、前置条件、效果、复杂度和异常保证。
3. 最后查看目标编译器官方文档，确认模块、并行算法等工具链相关能力的构建方式。

提案记录的是某个时间点的设计。特性进入标准后仍可能通过后续提案和缺陷报告修改，因此提案不能替代最终规范文本。

工作草案描述当前标准演进状态，可能包含后续版本或缺陷修复。阅读 C++11–C++23 文档时，必须结合发布版草案和版本变化论文确认某个接口在哪一版首次可用，不能直接把当前章节中的所有成员当作初版接口。

## 发布版本、缺陷修正与实现支持

区分三个问题：特性首次进入哪个标准、该标准后来是否经过缺陷修正、当前编译器与标准库是否实现了它。提案写于某一年，不代表一定属于下一版标准；缺陷修正常回溯到已经发布的版本。

本仓库的具体核对入口包括：

- [标准库移动后状态](https://eel.is/c++draft/lib.types.movedfrom)：通常有效但值未指定，满足前置条件的操作仍可用；自定义类型需要自己的契约。
- [P1094R2](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1094r2.html)：C++20 的嵌套内联命名空间语法，不能写成 C++17 已有能力。
- [P2325R3](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p2325r3.html)：移除 View 的默认构造要求，相关迭代器与适配器随之调整。
- [P2415R2](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p2415r2.html)：针对 C++20 的 Ranges 缺陷修正，包含 owning_view 与可拥有右值范围的处理。
- [P2210R2](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p2210r2.html)：调整 split_view，并以 lazy_split_view 保留原有设计；它们的现代接口不等于发布初版接口。
- [协程句柄恢复与销毁](https://eel.is/c++draft/coroutine.handle.resumption)、[constinit](https://eel.is/c++draft/dcl.constinit)：核对前置条件与声明限制，再结合版本提案阅读。

`-std=c++20` 选择语言模式，不会安装较新的标准库，也不能证明所有缺陷修正、时区数据库或工具链专用构建能力已可用。文档示例应明确依赖，并通过实际编译验证。

## WG21 官方入口

- [WG21 官方网站](https://www.open-std.org/jtc1/sc22/wg21/)
- [WG21 论文索引](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/)
- [C++ 工作草案可导航版本](https://eel.is/c++draft/)

## 版本变化总览

- [C++11 后发布的工作草案 N3337](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)
- [P1319R0：C++11 到 C++14 的变化](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)
- [P0636R3：C++14 到 C++17 的变化](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)
- [P2131R0：C++17 到 C++20 的变化](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)
- [N4950：C++23 工作草案](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2023/n4950.pdf)

## C++23 与工具链支持

[C++23 入口](cpp23/README.md)区分首次标准化的接口、后续扩展及实现支持。各专题引用对应 WG21 章节；涉及版本边界时结合 N4950 与提案阅读。`mdspan::at`、`runtime_format`、`function_ref` 等后续能力不能冒充初版 C++23 接口。

示例的可选 `requires` 元数据依据标准[特性测试宏](https://eel.is/c++draft/version.syn)声明。宏满足后仍需实际编译、链接并运行，宏缺失只表示此次按声明未验证，不能替代技术审阅或证明特性不存在。

- [Clang 语言支持](https://clang.llvm.org/cxx_status)
- [libc++ C++23 状态](https://libcxx.llvm.org/Status/Cxx23.html)
- [libstdc++ 标准支持](https://gcc.gnu.org/onlinedocs/libstdc++/manual/status.html)

## 引用要求

- 每篇专题至少链接一个对应的工作草案章节。
- 有独立提案的特性应同时链接最接近最终采用版本的提案。
- 正文必须明确哪些结论是标准保证，哪些只是典型实现。
- 工具链命令只能引用 GCC、Clang、MSVC 或构建系统官方文档。
- 不复制外部资料的大段原文，只总结与本专题直接相关的规范事实。
