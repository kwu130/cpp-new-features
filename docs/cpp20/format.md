# `format`

`std::format` 以类型安全的占位符替代易错的格式化字符串和冗长的流状态设置。

<!-- example id="cpp20-format" std="c++20" file="main.cpp" kind="single" compilers="all" output="20 + 22 = 42" -->
```cpp
#include <format>
#include <iostream>

int main() {
    std::cout << std::format("{} + {} = {}", 20, 22, 42) << '\n';
}
```

格式字符串在可行时接受编译期检查。若格式来自运行期输入，应使用对应运行期格式接口并处理错误。标准库对 `<format>` 的完整实现时间存在差异，验证矩阵会据实际工具链结果决定是否需要标记兼容边界。

