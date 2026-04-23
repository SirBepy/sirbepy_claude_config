param(
    [Parameter(Mandatory=$true)]
    [string]$HtmlPath,

    [Parameter(Mandatory=$false)]
    [string]$TextPath
)

Add-Type -AssemblyName System.Windows.Forms

$fragment = Get-Content -Path $HtmlPath -Raw

$prefix = "<html>`r`n<body>`r`n<!--StartFragment-->`r`n"
$suffix = "`r`n<!--EndFragment-->`r`n</body>`r`n</html>"

$headerTemplate = "Version:0.9`r`nStartHTML:{0:D10}`r`nEndHTML:{1:D10}`r`nStartFragment:{2:D10}`r`nEndFragment:{3:D10}`r`n"

$utf8 = [System.Text.Encoding]::UTF8

$placeholderHeader = [string]::Format($headerTemplate, 0, 0, 0, 0)
$headerLen = $utf8.GetByteCount($placeholderHeader)
$prefixLen = $utf8.GetByteCount($prefix)
$fragmentLen = $utf8.GetByteCount($fragment)
$suffixLen = $utf8.GetByteCount($suffix)

$startHTML = $headerLen
$startFragment = $startHTML + $prefixLen
$endFragment = $startFragment + $fragmentLen
$endHTML = $endFragment + $suffixLen

$header = [string]::Format($headerTemplate, $startHTML, $endHTML, $startFragment, $endFragment)

$cfHtml = $header + $prefix + $fragment + $suffix
$bytes = $utf8.GetBytes($cfHtml)
$stream = New-Object System.IO.MemoryStream(,$bytes)

$dataObject = New-Object System.Windows.Forms.DataObject
$dataObject.SetData("HTML Format", $stream)

if ($TextPath -and (Test-Path $TextPath)) {
    $text = Get-Content -Path $TextPath -Raw
    $dataObject.SetText($text, [System.Windows.Forms.TextDataFormat]::UnicodeText)
}

[System.Windows.Forms.Clipboard]::SetDataObject($dataObject, $true)
