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

