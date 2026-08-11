# 字符串和容器常用增强

字符串加入 `starts_with`、`ends_with`，关联容器加入 `contains`，并提供统一的 `erase`/`erase_if`，让常见意图更直接。

<!-- example id="cpp20-library-conveniences" std="c++20" file="main.cpp" kind="single" compilers="all" output="valid=true, remaining=2" -->
```cpp
#include <iostream>
#include <map>
#include <string>
#include <vector>

int main() {
    const std::string filename = "report.md";
    const std::map<std::string, int> versions{{"cpp20", 20}};
    std::vector<int> values{1, 2, 3, 4};
    std::erase_if(values, [](int value) { return value % 2 == 0; });

    const bool valid = filename.starts_with("report")
        && filename.ends_with(".md")
        && versions.contains("cpp20");
    std::cout << "valid=" << std::boolalpha << valid
              << ", remaining=" << values.size() << '\n';
}
```

`contains` 只回答键是否存在，不返回元素；随后还要访问值时，单次 `find` 更合适。前后缀检查按字符序列比较，不处理路径规范化或大小写规则。

## `starts_with` 与 `ends_with`

字符串和 `string_view` 的前后缀检查接受字符、字符串视图等形式，语义是长度检查后比较对应字符区间。复杂度与被比较前后缀长度线性相关，不进行区域设置、Unicode 规范化或大小写折叠。

解析协议固定 ASCII 标记时它们很合适；处理用户自然语言、文件系统大小写或组合 Unicode 字符时需要更高层文本库。后缀名判断也不等于安全文件类型验证。

## 关联容器 `contains`

`contains(key)` 等价于 `find(key) != end()` 的意图表达，复杂度沿用容器查找：有序关联容器通常 O(log n)，无序容器平均 O(1)。透明比较器存在时可进行异构查找，避免临时构造完整键类型。

若检查后立即再次 `at` 或 `find`，会做两次查找且并发外部修改时可能有竞态。需要元素时直接保存一次 `find` 结果；只需布尔判断才用 `contains`。

## `erase` 与 `erase_if`

统一非成员 `erase(container, value)` 和 `erase_if(container, predicate)` 封装不同容器正确的删除惯用法，并返回删除数量。对 `vector` 等顺序容器通常执行移动压缩，复杂度 O(n)，被删位置后的引用和迭代器失效。

谓词可能按实现需要被调用，不能修改容器结构或依赖固定调用次数。删除大型对象会执行析构和移动，批量操作仍应评估延迟峰值。

## 示例解析与工程实践

示例组合字符串检查、映射存在性和向量条件删除。便利接口减少样板代码，但不会改变底层复杂度、编码语义或失效规则。代码审查仍需问：是否重复查找、文本规则是否足够、删除后是否保存了悬空迭代器，以及谓词是否纯净。
