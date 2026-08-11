# `source_location`

`source_location` 以标准方式捕获调用点的文件、行号和函数名，适合日志、断言和诊断接口。

<!-- example id="cpp20-source-location" std="c++20" file="main.cpp" kind="single" compilers="all" output="message=ready, line-positive=true" -->
```cpp
#include <iostream>
#include <source_location>
#include <string_view>

void log(std::string_view message,
         const std::source_location location = std::source_location::current()) {
    std::cout << "message=" << message
              << ", line-positive=" << std::boolalpha << (location.line() > 0) << '\n';
}

int main() {
    log("ready");
}
```

默认参数必须在接口处调用 `current()` 才能取得调用者位置；若在函数体内调用，记录到的将是日志函数自身位置。文件路径可能包含构建环境信息，公开日志前应考虑脱敏。

## 捕获时机

`source_location::current()` 是特殊的静态工厂。用作默认实参时，它在调用表达式处形成位置，因此包装函数能看到调用者；在函数体普通语句中调用只会记录该语句自身。

对象通常保存文件名、函数名的静态字符串指针以及行列整数，复制廉价且不分配。标准不规定具体表示，也不保证列号或函数名格式在所有编译器一致。

## 与预处理宏比较

传统 `__FILE__`、`__LINE__` 宏也捕获展开位置，但封装日志函数时常需要宏继续把调用点传入。`source_location` 可通过普通默认参数完成，保持类型检查、命名空间和函数重载能力。

宏仍可能用于编译器不支持的旧标准或要求调用点表达式文本的断言。两者混用时应统一日志字段格式。

## 路径、可复现构建与隐私

`file_name()` 可能是绝对构建路径，泄露用户名、工作区或内部目录，并使不同机器构建产物不完全可复现。可通过编译器前缀映射选项、构建系统根路径裁剪或日志落盘前规范化处理。

函数名格式可能包含模板实参和编译器特有修饰，适合诊断但不应作为稳定协议键。行号也会随源码编辑变化，日志聚合最好搭配稳定事件 ID。

## 示例解析与实践

示例只验证行号为正，避免把具体行号写成脆弱输出。工程日志接口可按值接收默认 location，异步日志需复制字符串内容还是只保存静态指针要根据工具链保证审查，并对外部可见日志执行路径脱敏。

## 权威资料

- [P1208R6：source_location](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1208r6.pdf)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
