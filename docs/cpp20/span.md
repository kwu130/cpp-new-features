# `span`

`span` 是连续内存的非拥有视图，可以统一接收数组、`array`、`vector` 或指针加长度，同时保留元素类型和边界信息。

<!-- example id="cpp20-span" std="c++20" file="main.cpp" kind="single" compilers="all" output="10" -->
```cpp
#include <array>
#include <iostream>
#include <span>

int sum(std::span<const int> values) {
    int result = 0;
    for (const int value : values) {
        result += value;
    }
    return result;
}

int main() {
    const std::array<int, 4> values{1, 2, 3, 4};
    std::cout << sum(values) << '\n';
}
```

`span` 不拥有内存，底层数据销毁或容器重新分配后视图会失效。只读参数使用 `span<const T>`；固定长度接口可以使用 `span<T, N>` 在类型中表达大小。

## 表示与静态长度

动态长度 `span<T>` 典型保存指针和元素数量；静态长度 `span<T, N>` 可只保存指针，因为 N 已在类型中。两者都不分配、不复制元素，按值传递通常廉价。

`span` 要求元素连续，能从内建数组、`array`、连续容器或指针加长度构造。它不会接受 `list` 等节点容器。长度以元素为单位，`size_bytes()` 才返回字节数。

## 子视图与边界

`first`、`last`、`subspan` 创建同一存储的窗口，不复制数据。编译期计数版本能把结果长度编码进类型，并在部分情况下提前检查；运行期越界仍违反前置条件，`operator[]` 不负责抛异常。

把对象表示为字节时可用 `as_bytes` 或 `as_writable_bytes`，它们保留合法别名规则接口，但字节序、填充和对象可序列化性仍由调用方处理。不能把任意对象内存直接当成跨平台协议。

## 生命周期与失效

`span` 比裸指针加长度更难把两者传错，却仍不拥有内存。`vector` 扩容、所有者析构、数组离开作用域都会使它失效。返回 span 时必须证明底层存储更长寿；异步保存参数 span 通常危险。

## API 设计与性能

只读算法按值接收 `span<const T>`，原地算法接收 `span<T>`。需要接受临时拥有容器并延长寿命时应使用拥有类型，而不是强行转换成 span。静态长度适合矩阵行、加密块等长度属于契约的接口。

示例让同一 `sum` 接受 `array`，生成代码接近指针循环。实践中同时测试空范围、固定长度和切片边界，并在文档中明确调用期间是否保存视图。
