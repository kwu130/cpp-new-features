# 容器增强

C++11 增加了固定长度 `array`、哈希容器，以及直接在容器存储区构造元素的 `emplace` 系列接口。

<!-- example id="cpp11-containers" std="c++11" file="main.cpp" kind="single" compilers="all" output="Ada=37, sum=6" -->
```cpp
#include <array>
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>

int main() {
    std::array<int, 3> values{{1, 2, 3}};
    std::unordered_map<std::string, int> ages;
    ages.emplace("Ada", 37);

    int sum = 0;
    for (const auto& value : values) {
        sum += value;
    }
    std::cout << "Ada=" << ages.at("Ada") << ", sum=" << sum << '\n';
}
```

`array` 大小属于类型的一部分且存储连续。无序容器只保证平均常数复杂度，不保证遍历顺序。`emplace` 可以避免临时对象，但并不天然比移动插入更快，应优先考虑可读性。

