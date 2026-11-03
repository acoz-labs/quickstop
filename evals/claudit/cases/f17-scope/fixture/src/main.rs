fn main() {
    let harbour = std::env::args().nth(1).unwrap_or_else(|| "Whitby".to_string());
    println!("{}: high water 06:42, low water 12:58 (local time)", harbour);
}
