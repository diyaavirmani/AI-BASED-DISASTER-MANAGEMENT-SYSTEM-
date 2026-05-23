# scripts/export_onnx.py — UPDATED

import torch
import onnxruntime
import numpy as np
import yaml
import time
from pathlib import Path


def export_to_onnx(checkpoint_path, output_path, config):
    """
    Exports the trained checkpoint to ONNX format.
    Run this ONCE after downloading the checkpoint from Colab.
    """
    device = torch.device('cpu')  # Export from CPU always

    arch = config['model']['architecture']
    if arch == 'unet':
        from src.models.unet import load_trained_model
    else:
        from src.models.hrnet import load_trained_model

    model = load_trained_model(checkpoint_path, config, device)
    model.eval()

    in_ch     = config['model']['in_channels']   # 9
    tile_size = config['model']['tile_size']      # 256

    dummy = torch.randn(1, in_ch, tile_size, tile_size)

    print(f"Exporting {arch} to ONNX...")
    torch.onnx.export(
        model, dummy, output_path,
        opset_version   = 17,
        input_names     = ['input'],
        output_names    = ['output'],
        dynamic_axes    = {
            'input':  {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    print(f"Exported to: {output_path}")
    return output_path


def validate_onnx(checkpoint_path, onnx_path, config):
    """Verify ONNX output matches PyTorch output."""
    device = torch.device('cpu')
    arch   = config['model']['architecture']
    if arch == 'unet':
        from src.models.unet import load_trained_model
    else:
        from src.models.hrnet import load_trained_model

    model = load_trained_model(checkpoint_path, config, device)
    model.eval()

    in_ch     = config['model']['in_channels']
    tile_size = config['model']['tile_size']
    dummy     = torch.randn(1, in_ch, tile_size, tile_size)

    with torch.no_grad():
        pt_out = model(dummy).numpy()

    sess   = onnxruntime.InferenceSession(str(onnx_path))
    ort_out = sess.run(None, {'input': dummy.numpy()})[0]

    max_diff = np.abs(pt_out - ort_out).max()
    passed   = max_diff < 1e-4

    print(f"Validation: {'✅ PASS' if passed else '❌ FAIL'}")
    print(f"Max output difference: {max_diff:.8f}")
    return passed


def benchmark(checkpoint_path, onnx_path, config, n_runs=100):
    """Compare PyTorch vs ONNX inference speed."""
    device = torch.device('cpu')
    arch   = config['model']['architecture']
    if arch == 'unet':
        from src.models.unet import load_trained_model
    else:
        from src.models.hrnet import load_trained_model

    model = load_trained_model(checkpoint_path, config, device)
    model.eval()

    in_ch     = config['model']['in_channels']
    tile_size = config['model']['tile_size']
    dummy     = torch.randn(1, in_ch, tile_size, tile_size)

    # PyTorch
    with torch.no_grad():
        t0 = time.time()
        for _ in range(n_runs):
            model(dummy)
        pt_ms = (time.time() - t0) * 1000 / n_runs

    # ONNX
    sess = onnxruntime.InferenceSession(str(onnx_path))
    t0 = time.time()
    for _ in range(n_runs):
        sess.run(None, {'input': dummy.numpy()})
    ort_ms = (time.time() - t0) * 1000 / n_runs

    speedup = pt_ms / ort_ms
    print(f"PyTorch: {pt_ms:.1f}ms/tile")
    print(f"ONNX:    {ort_ms:.1f}ms/tile")
    print(f"Speedup: {speedup:.2f}x")


if __name__ == '__main__':
    with open('configs/config.yaml') as f:
        config = yaml.safe_load(f)

    ckpt_path = config['paths']['active_checkpoint']
    onnx_path = Path(ckpt_path).with_suffix('.onnx')

    export_to_onnx(ckpt_path, str(onnx_path), config)
    validate_onnx(ckpt_path, onnx_path, config)
    benchmark(ckpt_path, onnx_path, config)

    # Update config to use ONNX for production inference
    print(f"\nONNX model ready: {onnx_path}")
    print("Update configs/config.yaml paths.active_checkpoint to the .onnx path")
    print("or keep the .pth path — tasks.py handles both formats")
